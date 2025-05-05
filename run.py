import os
from pathlib import Path
import sys
import httpx
from pydantic import SecretStr
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from langchain_openai import ChatOpenAI
from browser_use import Agent
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
#controller
from prism_configs.prism_controller import controller
#browser
from prism_configs.prism_browser import browser,context
from prism_configs.prism_prompts import glossary
#informacoes pessoais
password = os.getenv("PASSWORD")
vdi_api_key: str = os.getenv("VDI_API_KEY") # type: ignore
sensitive_data = {'x_name': "JULIA_MENEZES", 'x_password': password}
      
max_failures = 10
        
initial_actions = [
	{'open_tab': {'url': 'https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home'}},
	{"go_to_url":{"url":"https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home"}},
	{"input_text":{"index":2,"text":"JULIA_MENEZES"}},
	{"input_text":{"index":3,"text":password}},
	{"click_element_by_index":{"index":5}}, 
	
]

llm= ChatOpenAI(
        base_url="https://genai-api-dev.dell.com/v1",
        model="llama-3-3-70b-instruct",
        api_key=SecretStr(vdi_api_key),
        http_async_client=httpx.AsyncClient(verify=False),
        timeout=30,
        
    )

agent = Agent(
# 		task=(
# 			"""
#    in https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home GIVEN the user is on the Change Objects landing page and has the necessary permissions to view and search for change objects, WHEN they select the 'STATUS' field in the search form and choose 'BF' as a search criterion, THEN the 'BF' status should be available as a search option in the 'Status' multiple selection field, and the search results should display all change objects with a status of 'BF' after clicking the 'GO' button.

#in https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home enter in change objectts landing page, and select effectivy date 03/03/2004 and in LOB select dell networking
#    """),
  task=(
			"""
   in https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home GIVEN the user is on the Change Objects landing page and has the necessary permissions to view and search for change objects, WHEN they select the 'STATUS' field in the search form and choose 'BF' as a search criterion, THEN the 'BF' status should be available as a search option in the 'Status' multiple selection field, and the search results should display all change objects with a status of 'BF' after clicking the 'GO' button.
   """),
		llm=llm,
		use_vision=False,
		max_failures=max_failures,
		initial_actions=initial_actions,
		validate_output=False,
		browser_context=context,
        #planner_llm=llm,
        #planner_interval=1,
		controller=controller,
        generate_gif=True,
		sensitive_data=sensitive_data,
        message_context=glossary,
	)
async def start_step_hook(agent: Agent):
    if agent.fail_or_unkown >= 3:
        print("ativa report jira")
        agent.stop()

async def end_step_hook(agent: Agent):
    if agent.state.history.is_done():
        if not agent.state.history.is_successful():
            print("ativa report jira")

async def main():

    history = await agent.run() # type: ignore
    #history = await agent.run() # type: ignore
    
    history.model_thoughts()
    input('Press Enter to close...')
    await context.close()
    await browser.close()

if __name__ == '__main__':
	asyncio.run(main())
 
 
 