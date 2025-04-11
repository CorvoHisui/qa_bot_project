from langgraph.graph import StateGraph
from tools.youtube_tool import get_youtube_transcript
from tools.chromadb_tool import store_embeddings
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from typing import Dict, Any, TypedDict
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain.chains import RetrievalQA

# Load environment variables from .env file
load_dotenv()

# Set environment variables for LangChain + OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT")

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
os.environ["LANGCHAIN_TRACING_V2"] = "true"

from langchain_groq import ChatGroq  # 👈 make sure you installed `langchain_groq`

def get_llm(provider="groq"):
    """Return an LLM instance based on the selected provider."""
    if provider == "groq":
        return ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama3-8b-8192"  # You can change to "mixtral-8x7b-32768" if needed
        )
    else:
        return ChatOpenAI(
            temperature=0,
            model="gpt-4-turbo-preview",
            max_tokens=1024
        )


# Define the state type for the graph using TypedDict instead of Dict
class GraphState(TypedDict, total=False):
    """State for the video processing graph."""
    urls: list
    all_chunks: list
    vector_store: Any
    agent: Any
    conversation_history: list  # Store conversation history

def get_user_query():
    """Function to prompt the user for input."""
    print("\nPlease enter your query about the videos (type 'exit' to quit):")
    query = input("Query: ")
    return query

def process_videos_node(state: Dict) -> Dict:
    """Node to process multiple videos and combine their transcripts."""
    print(f"State at start of process_videos_node: {state}")  # Debugging line
    
    # Ensure that the 'urls' field is correctly passed
    urls = state.get("urls", [])
    if not urls:
        raise ValueError("No URLs found in state.")
    
    all_chunks = []
    
    for url in urls:
        try:
            print(f"Processing video: {url}")
            transcript = get_youtube_transcript(url)
            
            # Create chunks from transcript
            for i in range(0, len(transcript), 100):
                chunk_text = " ".join(transcript[i:i+100])
                all_chunks.append(Document(
                    page_content=chunk_text,
                    metadata={"source": url}
                ))
            
            print(f"Successfully processed video: {url}")
        except Exception as e:
            print(f"Error processing video {url}: {e}")
            print("Continuing with other videos...")
    
    # Create a new state dictionary instead of modifying the existing one
    return {"urls": urls, "all_chunks": all_chunks}

def store_embeddings_node(state: Dict) -> Dict:
    """Node to store embeddings in ChromaDB."""
    print(f"State at start of store_embeddings_node: {state}")  # Debugging line
    
    all_chunks = state.get("all_chunks", [])
    if not all_chunks:
        raise ValueError("No valid chunks found from any videos")
    
    # Store embeddings in ChromaDB
    collection_name = "multiple_videos_collection"
    vector_store = store_embeddings(all_chunks, collection_name=collection_name)
    
    # Create a new state dictionary with all previous keys plus the new one
    return {**state, "vector_store": vector_store}

def create_agent_node(state: Dict) -> Dict:
    """Node to create QA agent with vector store."""
    print(f"State at start of create_agent_node: {state}")  # Debugging line
    
    vector_store = state.get("vector_store")
    if not vector_store:
        raise ValueError("No vector store found in state.")
    
    # Create LLM with lower temperature to reduce creativity
    llm = ChatOpenAI(
        temperature=0,  # Zero temperature for deterministic outputs
        model="gpt-4-turbo-preview",
        max_tokens=1024
    )
    
    # Increase k to get more context from the videos
    retriever = vector_store.as_retriever(search_kwargs={"k": 8})
    
    # Create a more restrictive QA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,  # Changed to True to help with verification
        verbose=True
    )
    
    # Create a wrapper function that enforces strict adherence to retrieved content
    def strict_qa_tool(query):
        try:
            result = qa_chain.invoke({"query": query})
            
            # Check if any documents were retrieved
            if not result.get("source_documents") or len(result.get("source_documents", [])) == 0:
                return "I don't have information about this in the video content."
            
            # Return only the result without source documents to the user
            return result["result"]
        except Exception as e:
            print(f"Error in QA tool: {e}")
            return "I couldn't find specific information about that in the video content."
    
    # Create a more restrictive tool
    retrieval_tool = Tool(
        name="video_transcript_qa",
        func=strict_qa_tool,
        description="ALWAYS use this tool to answer questions about the video content. This is the ONLY source of information you have."
    )
    
    tools = [retrieval_tool]
    
    # Create an even more restrictive system prompt
    system_prompt = """You are a specialized assistant that ONLY answers questions based on the transcripts of provided YouTube videos.

CRITICAL RULES YOU MUST FOLLOW:
1. You have NO knowledge beyond what is in the video transcripts.
2. You can ONLY provide information that is EXPLICITLY mentioned in the video transcripts.
3. If the information is not in the transcripts, you MUST respond with EXACTLY: "I don't have that information in the video content."
4. You MUST use the video_transcript_qa tool for EVERY question without exception.
5. NEVER make up information or use general knowledge.
6. If asked about topics unrelated to the videos, respond with EXACTLY: "I can only answer questions about the content of the provided videos."
7. Do not reference external sources, websites, or any information not in the videos.
8. Do not offer opinions or interpretations beyond what is directly stated in the videos.

Your ONLY purpose is to retrieve and provide information from the video transcripts."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="conversation_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_openai_functions_agent(llm=llm, tools=tools, prompt=prompt)
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,  # Increased from 1 to 3
        early_stopping_method="generate",  # Changed from "force" to "generate"
        return_intermediate_steps=False  # Changed to False for cleaner output
    )
    
    # Create a new state dictionary with all previous keys plus the new one
    return {**state, "agent": agent_executor, "conversation_history": []}

def build_graph_and_agent(urls):
    """Build the graph and agent for the Streamlit app."""
    try:
        # Create LangGraph builder with state schema
        builder = StateGraph(GraphState)
        
        # Add nodes
        builder.add_node("process_videos", process_videos_node)
        builder.add_node("store_embeddings", store_embeddings_node)
        builder.add_node("create_agent", create_agent_node)
        
        # Connect nodes
        builder.set_entry_point("process_videos")
        builder.add_edge("process_videos", "store_embeddings")
        builder.add_edge("store_embeddings", "create_agent")
        
        # Compile the graph
        graph = builder.compile()
        
        # Execute the graph with the initial state as a simple dictionary
        final_state = graph.invoke({"urls": urls})
        
        # Get the agent from the final state
        qa_agent = final_state["agent"]
        
        return qa_agent
        
    except Exception as e:
        raise Exception(f"Error building agent: {e}")

def main():
    # Get list of YouTube URLs
    urls = []
    print("Enter YouTube URLs (one per line, type 'done' when finished):")
    
    while True:
        url = input()
        if url.lower() in ['done', 'exit', 'quit']:
            break
        urls.append(url)
    
    if not urls:
        print("No URLs provided. Exiting.")
        return
    
    try:
        # Create LangGraph builder with state schema
        builder = StateGraph(GraphState)
        
        # Add nodes
        builder.add_node("process_videos", process_videos_node)
        builder.add_node("store_embeddings", store_embeddings_node)
        builder.add_node("create_agent", create_agent_node)
        
        # Connect nodes
        builder.set_entry_point("process_videos")
        builder.add_edge("process_videos", "store_embeddings")
        builder.add_edge("store_embeddings", "create_agent")
        
        # Compile the graph
        graph = builder.compile()
        
        # Execute the graph with the initial state as a simple dictionary
        final_state = graph.invoke({"urls": urls})
        
        # Get the agent from the final state
        qa_agent = final_state["agent"]
        conversation_history = final_state["conversation_history"]
        
        # Define system prompt to explain the task
        system_prompt = """
        Welcome to the Video QA Bot!
        You can ask questions related to the content of the videos you provided.
        To quit, just type 'exit'.
        """
        
        print(system_prompt)
        
        while True:
            # Get user query
            query = get_user_query()
            
            # If user types 'exit', break out of the loop
            if query.lower() == 'exit':
                print("Goodbye!")
                break
            
            # Update the conversation history with the new user query
            conversation_history.append({"role": "user", "content": query})
            
            # Get response from the QA agent, including the conversation history
            try:
                response = qa_agent.invoke({
                    "input": query,
                    "conversation_history": conversation_history
                })
                
                # Print the answer
                if "output" in response:
                    print(f"\nAnswer: {response['output']}\n")
                else:
                    print(f"\nAnswer: {response}\n")
                
                # Update the conversation history with the agent's response
                conversation_history.append({"role": "assistant", "content": response['output']})
            except Exception as e:
                print(f"\nError getting response: {e}\n")
                print("Please try a different question.")
            
    except Exception as e:
        print(f"Error in processing: {e}")
        print("Please try different video URLs.")

if __name__ == "__main__":
    main()
