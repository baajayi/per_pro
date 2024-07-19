import os
from dotenv import load_dotenv
import anthropic
import google.generativeai as genai
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain.text_splitter import CharacterTextSplitter

# Load environment variables
load_dotenv()
genai.configure(api_key=os.environ['OPENAI_API_KEY'])

# Initialize the Claude client
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Load and prepare documents
loader = UnstructuredMarkdownLoader("data/2024-04-13holland.md")
documents = loader.load()

text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
docs = text_splitter.split_documents(documents)

# Initialize embeddings and create vector store
embeddings = HuggingFaceEmbeddings()
vectorstore = FAISS.from_documents(docs, embeddings)

def rag_with_claude(query: str):
    # Retrieve relevant documents
    relevant_docs = vectorstore.similarity_search(query, k=3)
    
    # Prepare context from retrieved documents
    context = "\n".join([doc.page_content for doc in relevant_docs])
    
    # Construct the prompt
    prompt = f"""Here is some context information:
    {context}
    
    Based on this context, please answer the following question:
    {query}
    
    If the context doesn't provide enough information to answer the question, 
    please say so and answer to the best of your ability based on your knowledge."""

    # Generate response using Claude
    model = genai.GenerativeModel(model_name='gemini-1.5-flash')
    response = model.generate_content(prompt)
    
    return response.text

# Example usage
query = "What is the painful Lesson President Holland Learned?"
result = rag_with_claude(query)
print(result)

# Optionally, save the vector store for future use
vectorstore.save_local("faiss_index")