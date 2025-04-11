from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from tools.youtube_tool import get_youtube_transcript
from tools.chromadb_tool import store_embeddings, query_vector_store
from agents.qa_agent import get_response

# 1. Node: Load transcript from URL
def load_transcript(state):
    url = state["url"]
    transcript = get_youtube_transcript.invoke(url)
    return {"transcript": transcript, "url": url}

# 2. Node: Chunk transcript
def process_chunks(state):
    # Ensure there are valid chunks from videos
    if not input.get("chunks"):
        raise ValueError("No valid chunks found from any videos")
    
    transcript = state["transcript"]
    chunks = [{"page_content": " ".join(transcript[i:i+100])} for i in range(0, len(transcript), 100)]
    return {"chunks": chunks, **state}

# 3. Node: Embed and store

def embed_and_store(state):
    vector_store = store_embeddings(state["chunks"])
    return {"vector_store": vector_store, **state}

# 4. Node: Ask a question
def ask_question(state):
    query = state["query"]
    vector_store = state["vector_store"]
    response = get_response(query, vector_store)
    return {"answer": response, **state}

# Build LangGraph
graph_builder = StateGraph()
graph_builder.add_node("load_video", RunnableLambda(load_transcript))
graph_builder.add_node("process_chunks", RunnableLambda(process_chunks))
graph_builder.add_node("embed_store", RunnableLambda(embed_and_store))
graph_builder.add_node("qa_node", RunnableLambda(ask_question))

# Set edges
graph_builder.set_entry_point("load_video")
graph_builder.add_edge("load_video", "process_chunks")
graph_builder.add_edge("process_chunks", "embed_store")
graph_builder.add_edge("embed_store", "qa_node")
graph_builder.add_edge("qa_node", END)

# Compile
qa_graph = graph_builder.compile()