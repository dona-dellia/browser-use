from typing import List
from agno.agent import Agent
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools
import httpx
import os
from agno.tools import tool
from dotenv import load_dotenv
from pydantic import SecretStr
from agno.storage.sqlite import SqliteStorage
from agno.tools.yfinance import YFinanceTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.serper import SerperTools

load_dotenv()

vdi_api_key: str = os.getenv("VDI_API_KEY") # type: ignore

model = OpenAIChat(
        base_url="https://genai-api-dev.dell.com/v1",
        http_client=httpx.Client(verify=False),
        id="llama-3-3-70b-instruct",
        api_key=vdi_api_key,
        
    )

memory = Memory(
    # Use any model for creating and managing memories
    model=model,
    # Store memories in a SQLite database
    db=SqliteMemoryDb(table_name="user_memories", db_file="tmp/agent.db"),
    # We disable deletion by default, enable it if needed
    delete_memories=True,
    clear_memories=True,
)

agent = Agent(
    model=OpenAIChat(
        base_url="https://genai-api-dev.dell.com/v1",
        http_client=httpx.Client(verify=False),
        id="llama-3-3-70b-instruct",
        api_key=vdi_api_key,
        
    ),
    tools=[
        ReasoningTools(add_instructions=True),
        YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True, company_news=True),
],
    # User ID for storing memories, `default` if not provided
    user_id="ava",
    instructions=[
        "Use tables to display data.",
        "Include sources in your response.",
        "Only include the report in your response. No other text.",
    ],
    memory=memory,
    # Let the Agent manage its memories
    enable_agentic_memory=True,
    markdown=True,
)
web_agent = Agent(
    name="Web Search Agent",
    role="Handle web search requests and general research",
    model=model,
    tools=[DuckDuckGoTools(),SerperTools()],
    instructions="Always include sources",
    add_datetime_to_instructions=True,
)
if __name__ == "__main__":
    # This will create a memory that "ava's" favorite stocks are NVIDIA and TSLA
    web_agent.print_response(
        """in https://webscraper.io/test-sites/e-commerce/allinone
Scrapes content from the webpage and show me the content""",markdown=True)

 