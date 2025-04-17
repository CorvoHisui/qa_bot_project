from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.tools import Tool
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

def create_qa_agent(llm, tools, prompt):
    """
    Create a structured chat agent using Groq LLM.
    This function replaces the OpenAI-specific agent creation.
    """
    # Create the agent
    agent = create_structured_chat_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )
    
    # Create the agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,
        early_stopping_method="generate",
        return_intermediate_steps=False
    )
    
    return agent_executor