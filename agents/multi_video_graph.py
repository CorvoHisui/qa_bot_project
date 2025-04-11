from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from tools.youtube_tool import get_youtube_transcript
from tools.chromadb_tool import store_embeddings
from qa_agent import get_response

# Node: fetch transcript + chunk + accumulate
import os
import pickle
from tqdm import tqdm
from tools.youtube_tool import get_youtube_transcript

# Cache folder
CACHE_DIR = "cache"

def load_video_transcripts_node(state):
    video_urls = state.get("video_urls", [])
    all_chunks = []
    
    # Ensure cache directory exists
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    # Check cache for each video URL
    for url in tqdm(video_urls, desc="Fetching transcripts"):
        cache_filename = os.path.join(CACHE_DIR, f"{url.split('v=')[1]}.pkl")
        
        # If cached data exists, load it
        if os.path.exists(cache_filename):
            with open(cache_filename, "rb") as f:
                chunks = pickle.load(f)
            tqdm.write(f"Loaded cached data for: {url}")
        else:
            transcript = get_youtube_transcript(url)
            chunks = [{"page_content": " ".join(transcript[i:i + 100])} for i in range(0, len(transcript), 100)]
            # Cache the chunks for future use
            with open(cache_filename, "wb") as f:
                pickle.dump(chunks, f)
            tqdm.write(f"Fetched new data for: {url}")

        all_chunks.extend(chunks)

    return {"video_chunks": all_chunks}


# Node: once all videos are processed
def build_agent_and_respond(state):
    vector_store = store_embeddings(state["all_chunks"])
    response = get_response(state["query"], vector_store)
    state["response"] = response
    return state

# Graph definition
def create_video_graph():
    builder = StateGraph()
    builder.add_node("process_video", RunnableLambda(process_video))
    builder.add_node("build_agent", RunnableLambda(build_agent_and_respond))

    # Conditional logic to decide next step
    def should_continue(state):
        return "process_video" if state["current_index"] < len(state["video_urls"]) else "build_agent"

    builder.set_entry_point("process_video")
    builder.add_conditional_edges("process_video", should_continue)
    builder.add_edge("build_agent", END)

    return builder.compile()
