import streamlit as st
from tools.utils import fetch_video_metadata
from main import build_graph_and_agent
import os

# Set up the page configuration
st.set_page_config(page_title="YouTube QA Bot", page_icon="🎥")

# Title and introduction
st.title("🎥 YouTube QA Bot")
st.markdown("""
    Paste the YouTube URL(s) below and ask questions about the videos you provide.
    
    **Note: This bot will ONLY answer questions using information directly from the videos. 
    If the information is not in the video content, it will tell you it doesn't know.**
""")

# Initialize session state variables if they don't exist
if "agent" not in st.session_state:
    st.session_state.agent = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "videos_submitted" not in st.session_state:
    st.session_state.videos_submitted = False
if "valid_urls" not in st.session_state:
    st.session_state.valid_urls = []

# Only show the URL input if videos haven't been submitted yet
if not st.session_state.videos_submitted:
    # Input box for YouTube URL(s)
    video_urls = st.text_area("Enter YouTube URLs (one per line)")
    
    # Define the submit button
    submit_btn = st.button("Submit")
    
    # When the button is clicked, process the URLs
    if submit_btn:
        # Process URLs when the button is clicked
        urls = [url.strip() for url in video_urls.strip().split("\n") if url.strip()]
        
        # Fetch metadata and check for valid data
        valid_urls = []
        for url in urls:
            metadata = fetch_video_metadata(url)
            if metadata:
                valid_urls.append(url)
                # Display video information in a cleaner format
                st.markdown(f"""
                    <div style="background-color:#f9f9f9; border-radius:8px; padding:10px; margin:15px 0; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                        <img src="{metadata['thumbnail_url']}" style="width:200px; height:120px; object-fit:cover; border-radius:8px; float:left; margin-right:15px;">
                        <h3 style="margin-top:0; color:#333333;">{metadata['title']}</h3>
                        <p style="color:#444444;">{metadata['description'][:150]}...</p>
                        <p style="color:#444444;"><strong>Views:</strong> {metadata['views']}</p>
                        <div style="clear:both;"></div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.warning(f"Could not fetch metadata for {url}. Please ensure the URL is valid.")
        
        if valid_urls:
            with st.spinner("Processing videos... This may take a minute."):
                # Initialize agent with valid URLs
                st.session_state.agent = build_graph_and_agent(valid_urls)
                st.session_state.valid_urls = valid_urls
                st.session_state.videos_submitted = True
                st.success("Videos processed successfully! You can now ask questions.")
                st.rerun()  # Updated from experimental_rerun to rerun
        else:
            st.error("No valid URLs provided.")
else:
    # Display the videos that were processed
    st.subheader("Processed Videos:")
    for url in st.session_state.valid_urls:
        metadata = fetch_video_metadata(url)
        if metadata:
            st.markdown(f"""
                <div style="background-color:#f9f9f9; border-radius:8px; padding:10px; margin:15px 0; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                    <img src="{metadata['thumbnail_url']}" style="width:200px; height:120px; object-fit:cover; border-radius:8px; float:left; margin-right:15px;">
                    <h3 style="margin-top:0; color:#333333;">{metadata['title']}</h3>
                    <div style="clear:both;"></div>
                </div>
            """, unsafe_allow_html=True)
    
    # Add a button to reset and add new videos
    if st.button("Process different videos"):
        st.session_state.videos_submitted = False
        st.session_state.agent = None
        st.session_state.chat_history = []
        st.session_state.valid_urls = []
        st.rerun()  # Updated from experimental_rerun to rerun

# Initialize chat UI if agent exists
if st.session_state.agent:
    st.markdown("---")
    st.subheader("Ask your questions below:")

    user_query = st.text_input("Your question:", key="user_input")
    ask_btn = st.button("Ask")

    if ask_btn and user_query:
        with st.spinner("Getting answer..."):
            try:
                # Modify how we invoke the agent to handle iteration limits
                response = st.session_state.agent.invoke({
                    "input": user_query  # Simplified query without prefix
                })
                
                # Extract the answer from the response
                if isinstance(response, dict) and "output" in response:
                    answer = response["output"]
                elif isinstance(response, str):
                    answer = response
                else:
                    answer = "I couldn't find specific information about that in the video content."
                
                # Add to chat history
                st.session_state.chat_history.append(("user", user_query))
                st.session_state.chat_history.append(("ai", answer))
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state.chat_history.append(("user", user_query))
                st.session_state.chat_history.append(("ai", "I couldn't find information about that in the video content."))
                answer = "Sorry, I couldn't process your question. Please try again."

    # Display chat history in reverse order (most recent at the top)
    if st.session_state.chat_history:
        st.markdown("### 💬 Chat History")
        
        # Process chat history in pairs (question-answer)
        history = list(reversed(st.session_state.chat_history))
        
        # Display messages in pairs (question followed by answer)
        for i in range(0, len(history), 2):
            if i+1 < len(history):  # Make sure we have both question and answer
                # Get the question and answer
                user_role, user_message = history[i]
                ai_role, ai_message = history[i+1]
                
                # Display question followed by answer (reversed order)
                if ai_role == "ai" and user_role == "user":
                    st.markdown(f"**You:** {user_message}")
                    st.markdown(f"**Bot:** {ai_message}")
                    st.markdown("---")
                else:  # Handle any potential misalignment
                    st.markdown(f"**{user_role.capitalize()}:** {user_message}")
                    st.markdown(f"**{ai_role.capitalize()}:** {ai_message}")
                    st.markdown("---")
            elif i < len(history):  # Handle odd number of messages (last question without answer)
                role, message = history[i]
                st.markdown(f"**{role.capitalize()}:** {message}")
                st.markdown("---")

