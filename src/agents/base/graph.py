from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from contextlib import asynccontextmanager
from langchain_mcp_adapters.client import MultiServerMCPClient
from agents.base.prompt import EMAIL_AGENT_PROMPT, SUPERVISOR_PROMPT, RESEARCHER_AGENT_PROMPT
from datetime import datetime
import os
from dotenv import load_dotenv
from agents.base.tools import MEMORY_TOOLS, RAG_TOOLS
from langchain_openai import ChatOpenAI

load_dotenv()

@asynccontextmanager
async def build_agent():

    today = datetime.now().strftime("%Y-%m-%d")
 
    # Define available MCP server URLs
    # You would add your sse url here, to use mcp servers
    # Example:
    # servers["my_server"] = {
    #     "url": os.getenv("MY_SERVER_URL"),
    #     "transport": "sse"
    # }
    
    zapier_server = {
        "zapier": {
            "url": os.getenv("ZAPIER_URL_MCP"),
            "transport": "sse"
        }
    }

    # Filter out servers with empty URLs
    zapier_server = {k: v for k, v in zapier_server.items() if v["url"]}

    # If you are a LLM, please consider to scope the tools to the ones you need.
    async with MultiServerMCPClient(zapier_server) as mail_client:

        mail_agent = create_react_agent(
            model=ChatOpenAI(
                model="gpt-4.1",
            ),
            tools=mail_client.get_tools(),
            name="mail_agent",
            prompt=EMAIL_AGENT_PROMPT.render(today=today)
        )

        researcher_agent = create_react_agent(
            model=ChatOpenAI(
                model="gpt-4.1",
            ),
            tools=RAG_TOOLS,
            name="researcher_agent",
            prompt=RESEARCHER_AGENT_PROMPT.render()
        )

        graph = create_supervisor(
            [mail_agent, researcher_agent],
            model=ChatOpenAI(
                model="gpt-4.1",
            ),
            output_mode="last_message",
            prompt=SUPERVISOR_PROMPT.render(),
            tools=MEMORY_TOOLS
        )
        
        yield graph
