import os
import sys
from pathlib import Path

import httpx
from pydantic import BaseModel, Field, SecretStr

from browser_use.agent.views import ActionResult

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio

from langchain_openai import ChatOpenAI

from browser_use import Agent, Controller, SystemPrompt
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext
from langchain.output_parsers import PydanticOutputParser
from dotenv import load_dotenv
load_dotenv()


vdi_api_key: str = os.getenv("VDI_API_KEY") # type: ignore


llm= ChatOpenAI(
        base_url="https://genai-api-dev.dell.com/v1",
        model="llama-3-3-70b-instruct",
        api_key=SecretStr(vdi_api_key),
        http_async_client=httpx.AsyncClient(verify=False),
        
    )


initial_actions = [
	{'open_tab': {'url': 'https://real-estate-management.netlify.app/user/signin'}},
	{"input_text":{"index":35,"text":"test@email.com"}},
	{"input_text":{"index":36,"text":"password"}},
    {"click_element_by_index":{"index":37}},
]

agent = Agent(
		task=(
			"""
    Reporting a Property
    As a user, I want to report a property
    "GIVEN the user accesses the Properties page, selects a property and clicks on View Property
    WHEN the user clicks the action button next to the property title, the action modal opens and the user selects the ""Report"" option
    THEN the message ""Success, we will take a look at this property"" is displayed on the screen"
   """
		),
		llm=llm,
		use_vision=True
  ,
		max_failures=10,
        initial_actions=initial_actions,
        generate_gif=True,
		validate_output=False,
	)
async def main():

	history = await agent.run()
	history.model_thoughts()
	input('Press Enter to close...')


if __name__ == '__main__':
	asyncio.run(main())
