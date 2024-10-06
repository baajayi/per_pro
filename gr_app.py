from flask import Flask, request, jsonify, render_template
import logging
import sys
import os
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
import yaml
from llama_index.core import StorageContext, PromptTemplate
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
# from IPython.display import Markdown, display
from dotenv import load_dotenv, find_dotenv

# logging.basicConfig(stream=sys.stdout, level=logging.INFO)
# logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))
_=load_dotenv(find_dotenv())

client = OpenAI()
pc = Pinecone()

def extract_metadata_from_markdown(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        
        if lines and lines[0].strip() == '---':
            end_index = None
            for i in range(1, len(lines)):
                if lines[i].strip() == '---':
                    end_index = i
                    break
            
            if end_index:
                yaml_content = ''.join(lines[1:end_index])
                metadata = yaml.safe_load(yaml_content)
                
                url = metadata.get('url', "https://www.churchofjesuschrist.org/study/general-conference/2024/04?lang=eng")
                author = metadata.get('author', None)
                if author:
                    author = author.replace('\xa0', ' ')
                
                return url, author
    
    return "https://www.churchofjesuschrist.org/study/general-conference/2024/04?lang=eng", None

def file_metadata_extractor(file_path):
    if file_path.endswith('.md'):
        url, author = extract_metadata_from_markdown(file_path)
        if url:
            return {'url': url, 'Author': author}
    return {}

index_name = "hy-sema"
existing_indexes = [index['name'].strip().lower() for index in pc.list_indexes()]
index_name_normalized = index_name.strip().lower()

if index_name_normalized not in existing_indexes:
    print(f"Index '{index_name}' does not exist. Creating a new index.")
    pc.create_index(index_name, dimension=1536, metric="dotproduct", spec=ServerlessSpec(cloud="aws", region="us-east-1"))
    
    # Only proceed with reading files and upserting vectors if the index is created
    docs = SimpleDirectoryReader("data1", file_metadata=file_metadata_extractor, recursive=True).load_data()
    embed_model = OpenAIEmbedding(model="text-embedding-ada-002")

    splitter = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=95,
        embed_model=embed_model
    )
    nodes = splitter.get_nodes_from_documents(docs)

    def add_metadata_to_nodes(nodes, docs):
        for node, doc in zip(nodes, docs):
            node.metadata = doc.metadata
        return nodes
    
    nodes_with_metadata = add_metadata_to_nodes(nodes, docs)

    hy_sema_index = pc.Index(index_name)
    vector_store = PineconeVectorStore(
        pinecone_index=hy_sema_index,
        add_sparse_vector=True,
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    def check_vector_exists(pinecone_index, doc_id):
        existing_vector = pinecone_index.fetch(ids=[doc_id])
        return existing_vector is not None and len(existing_vector['vectors']) > 0

    for node in nodes_with_metadata:
        doc_id = node.id_  # Assuming 'id' is the unique identifier for each document
        if not check_vector_exists(hy_sema_index, doc_id):
            # Upsert only if the vector does not exist
            vector_index = VectorStoreIndex(nodes=[node], embed_model=embed_model, storage_context=storage_context)
        else:
            print(f"Vector for document {doc_id} already exists, skipping upsert.")
    
    vector_index = VectorStoreIndex(nodes=nodes_with_metadata, embed_model=embed_model, storage_context=storage_context)
else:
    print(f"Index '{index_name}' already exists. Connecting to the existing index.")
    hy_sema_index = pc.Index(index_name)
    vector_index = VectorStoreIndex(nodes=[], embed_model=OpenAIEmbedding(model="text-embedding-ada-002"), storage_context=StorageContext.from_defaults(vector_store=PineconeVectorStore(pinecone_index=hy_sema_index, add_sparse_vector=True)))

query_engine = vector_index.as_query_engine(response_mode="tree_summarize", model="gpt-4o-mini", similarity_top_k=2)
meta_tmpl_str ="""
You are an AI assistant tasked with answering questions about the April 2024 General Conference of the Church of Jesus Christ of Latter-Day Saints. You will be provided with the content of the conference talks and a question to answer. Your goal is to provide accurate and relevant information based solely on the content of these talks.

Here is the content of the conference talks:

<conference_talks>
{{CONFERENCE_TALKS}}
</conference_talks>

When answering questions, follow these guidelines:

1. Carefully read and analyze the conference talks to find relevant information and think deeply how the relevant information can be used to answer the question.
2. Only use information explicitly stated in the provided talks. Do not include external knowledge or personal interpretations.
3. If the question cannot be answered using the information in the talks, state that the answer is not found in the provided content.
4. Provide direct quotes from the talks when possible to support your answer. Use quotation marks and indicate the speaker's name for each quote.
5. If multiple talks address the question, synthesize the information from all relevant sources.
6. Maintain a respectful and reverent tone when discussing religious topics.

Be as concise and complete as possible

Use the following XML tags to structure your response:
<answer><main_content></main_content><limitations></limitations>
</answer>

Now, please answer the following question based on the conference talks provided:

<question>
{{QUESTION}}
</question>"""

meta_tmpl = PromptTemplate(meta_tmpl_str)

query_engine.update_prompts(
    {"response_synthesizer:summary_template": meta_tmpl}
)

prompts_dict = query_engine.get_prompts()
query_engine = vector_index.as_query_engine(response_mode="tree_summarize", similarity_top_k=2, model="gpt-4o-mini")

# def display_prompt_dict(prompts_dict):
#     for k, p in prompts_dict.items():
#         text_md = f"**Prompt Key**: {k}<br>" f"**Text:** <br>"
#         display(Markdown(text_md))
#         print(p.get_template())
#         display(Markdown("<br><br>"))

# display_prompt_dict(prompts_dict)



# import pandas as pd

# def generate_answers(input_csv_path, output_csv_path):
#     """
#     Reads a CSV file with columns 'question', 'answer', and 'quotes', uses the query engine
#     to generate an answer for each question, appends the generated answer to a new column
#     'generated answer', and writes the updated DataFrame to a new CSV file.

#     Args:
#         input_csv_path (str): The path to the input CSV file.
#         output_csv_path (str): The path to the output CSV file.

#     Returns:
#         None
#     """
#     # Read the CSV file into a DataFrame
#     df = pd.read_csv(input_csv_path, encoding='latin1')
    
#     # Check if 'question' column exists
#     if 'question' not in df.columns:
#         print("The CSV file must contain a 'question' column.")
#         return
    
#     # Initialize a list to store generated answers
#     generated_answers = []
#     sources = []
    
#     # Iterate over each row in the DataFrame
#     for index, row in df.iterrows():
#         question = row['question']
#         print(f"Processing question {index + 1}/{len(df)}: {question}")
        
#         # Use the query engine to generate an answer
#         try:
#             response = query_engine.query(question)
#             generated_answer = response.response  # Extract the answer text from the response
#             source = '\n\n\n'.join([node.text for node in response.source_nodes])
#         except Exception as e:
#             print(f"An error occurred while processing question '{question}': {e}")
#             generated_answer = None  # or you can set a default value or error message
        
#         # Append the generated answer to the list
#         generated_answers.append(generated_answer)
#         sources.append(source)
    
#     # Add the 'generated answer' column to the DataFrame
#     df['generated answer'] = generated_answers
#     df['Sources'] = sources
    
#     # Write the updated DataFrame to a new CSV file
#     df.to_csv(output_csv_path, index=False)
    
#     print(f"Generated answers have been saved to {output_csv_path}")


# # Define the input and output CSV file paths
# input_csv = 'que_and_a.csv'
# output_csv = 'output_with_generated_answers.csv'

# # Call the function to generate answers
# generate_answers(input_csv, output_csv)




app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        query = request.form['query']
        response = query_engine.query(query)
        print(response.source_nodes)

        # Extracting metadata and response content
        results = []
        for source in response.source_nodes:
            url = source.node.metadata.get("url", "N/A")
            author = source.node.metadata.get("Author", "N/A")
            content = source.node.get_text()
            results.append({"content": content, "url": url, "author": author})
        
        # Pass query and results to the template
        return render_template('index.html', query=query, response=response, results=results)
    
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
