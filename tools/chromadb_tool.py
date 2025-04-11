# tools/chromadb_tool.py

# Use LangChain's tools instead of LangGraph
from langchain.tools import Tool
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# Assuming you have functions for embeddings and storing vectors
def store_embeddings(documents, collection_name=None):
    """Store document embeddings in ChromaDB."""
    # Create embeddings
    embeddings = OpenAIEmbeddings()
    
    # If no collection name is provided, use a default
    if collection_name is None:
        collection_name = "default_collection"
    
    # Make collection name safe for ChromaDB (alphanumeric and underscores only)
    import re
    import os
    import shutil
    
    safe_collection_name = re.sub(r'[^a-zA-Z0-9_]', '_', collection_name)
    
    # Create a separate directory for each collection
    db_path = f"./db/{safe_collection_name}"
    
    # Remove the directory if it exists
    if os.path.exists(db_path):
        try:
            shutil.rmtree(db_path)
            print(f"Removed existing database at {db_path}")
        except Exception as e:
            print(f"Warning: Could not remove existing database: {e}")
    
    # Ensure the directory exists
    os.makedirs(db_path, exist_ok=True)
    
    # Create a new vector store in the dedicated directory
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=safe_collection_name,
        persist_directory=db_path
    )
    
    return vector_store

# Function to query ChromaDB for relevant chunks
def query_chromadb(query, vector_store, k=5):
    # Query the vector store and retrieve the top 'k' most relevant chunks
    results = vector_store.similarity_search(query, k=k)
    return results
