from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import Tool
from langchain_community.chat_models import ChatOpenAI  # Updated import
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma

# Define a proper QA model function
def qa_model(query):
    """Answer questions using the stored video transcript."""
    llm = get_llm("groq")  # or "openai" to switch

    # Return a direct answer from the LLM
    return llm.invoke(query).content
