# app/agent.py
import os
from typing import List, Dict, Any
from langchain_core.tools import tool
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Initialize LLM
api_key = os.environ.get("GEMINI_API_KEY", "")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.3,
    google_api_key=api_key
)

@tool
def query_knowledge_base(query: str) -> str:
    """
    Queries the official MSME knowledge base/vector database for schemes details, eligibility, benefits, and portal URLs.
    """
    from app.knowledge_base import retrieve_context
    return retrieve_context(query, k=4)

@tool
def compare_msme_schemes(query: str) -> str:
    """
    Generates a side-by-side comparison of different government schemes like PMEGP, MUDRA, CGTMSE, etc.
    """
    from app.comparison import generate_comparison
    comp = generate_comparison(query)
    if not comp:
        return "No direct comparison found in comparison database."
    return str(comp)

# Set tools
tools = [query_knowledge_base, compare_msme_schemes]

# Prompt template for ReAct agent
template = """
You are MSME Saathi, an official AI-powered assistant.
Your goal is to help Indian citizens understand government schemes, registrations, policies, and track grievances.

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

CRITICAL RULES:
1. All thoughts, actions, and the Final Answer MUST be written in 100% standard English only.
2. The user question may be in Hindi, Bengali, or English. You must understand it but you MUST respond in English.
3. Under no circumstances should you mix Hindi/Devanagari, Bengali, or Hinglish words in the Final Answer.
4. Do NOT output your internal thoughts or tool observations inside the "Final Answer:" section. Write only the direct answer to the user's question.

Begin!

Chat History:
{chat_history}

Question: {input}
Thought: {agent_scratchpad}
"""

prompt = PromptTemplate.from_template(template)

# Create agent
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True
)

async def agent_chat(message: str, chat_history: list) -> str:
    """
    Executes the LangChain ReAct agent and returns its text response.
    """
    # Format chat history for prompt
    formatted_history = ""
    for msg in chat_history[-10:]: # Limit history size
        role = "User" if msg["role"] == "user" else "Assistant"
        formatted_history += f"{role}: {msg['content']}\n"
        
    result = await agent_executor.ainvoke({
        "input": message,
        "chat_history": formatted_history
    })
    return result["output"]
