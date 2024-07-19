# app.py
from flask import Flask, request, render_template
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core import Settings
from dotenv import load_dotenv, find_dotenv
import os

# Load environment variables
_ = load_dotenv(find_dotenv())

app = Flask(__name__)

# Load documents and create index
documents = SimpleDirectoryReader("./data").load_data()
Settings.text_splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
index = VectorStoreIndex.from_documents(
    documents,
    transformations=[SentenceSplitter(chunk_size=1024, chunk_overlap=20)],
)
query_engine = index.as_query_engine(similarity_top_k=2)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        query = request.form['query']
        response = query_engine.query(query)
        return render_template('index.html', query=query, response=response)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
