from flask import Flask, request, render_template
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from dotenv import load_dotenv, find_dotenv
import os

# Load environment variables
_ = load_dotenv(find_dotenv())

app = Flask(__name__)

# Load documents and create index
documents = SimpleDirectoryReader("data1", recursive=True).load_data()
index = VectorStoreIndex.from_documents(
    documents,
    transformations=[SentenceSplitter(chunk_size=1024, chunk_overlap=20)],
)
query_engine = index.as_query_engine(similarity_top_k=2, model="gpt-4o-mini")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        query = request.form['query']
        # Get the response from the query engine
        response = query_engine.query(query)
        
        # Extract relevant attributes (assuming response is a structured object)
        if isinstance(response, dict):
            # Handle case where response is a dictionary
            results = [
                {
                    "url": result.get("url", "N/A"),
                    "author": result.get("author", "N/A"),
                    "content": result.get("content", "No content available.")
                }
                for result in response.get("results", [])
            ]
        else:
            # If the response is a single object or plain text, treat it as a single response
            results = [{"content": str(response), "url": "N/A", "author": "N/A"}]

        return render_template('index1.html', query=query, response=response, results=results)

    return render_template('index1.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
