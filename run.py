import os
import sys
from pathlib import Path

import httpx
from pydantic import BaseModel, Field, SecretStr
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio

from langchain_openai import ChatOpenAI

from browser_use import Agent, Controller, ActionResult, Browser
from browser_use.browser.context import BrowserContext
from langchain.output_parsers import PydanticOutputParser
from dotenv import load_dotenv
from browser_use.browser.context import BrowserContextConfig
logger = logging.getLogger(__name__)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

load_dotenv()
#controle
controller = Controller(exclude_actions=['search_google'], save_py="code", save_selenium_code="output/")

@controller.action('Assert content of a page based on the description and the html')
async def assert_content(
    expectation: str,  
    browser: Browser,  
    page_assertion_llm: BaseChatModel  
):
    page = await browser.get_current_page() # type: ignore

    import markdownify
    page_content = markdownify.markdownify(await page.content())

    prompt = (
        "Your task is to validate whether the following expectation is met by the content of a web page.\n\n"
        "Expectation:\n"
        "{expectation}\n\n"
        "Page content:\n"
        "{page_content}\n\n"
        "Respond with sucess if the expectation is met and NO if it is not sucess."
    )
    print(f'prompt: {prompt}\n')
    template = PromptTemplate(
        input_variables=['expectation', 'page_content'],
        template=prompt
    )

    try:
        response = page_assertion_llm.invoke(template.format(
            expectation=expectation,
            page_content=page_content
        ))

        msg = f'✅ Verification result:\n{response}\n'
        logger.info(msg)

        return ActionResult(extracted_content=msg, include_in_memory=True)

    except Exception as e:
        logger.debug(f'❌ Assert error: {e}')
        msg = f'❌ verification error.\n'
        logger.info(msg)
        return ActionResult(extracted_content=msg)

@controller.action('Decision-Making with Uncertainty Handling')
def uncertainty_handling(answer: str) -> ActionResult:
    return ActionResult(extracted_content=answer)

controller = Controller(exclude_actions=['search_google'], save_py="code", save_selenium_code="output/")


#browser
config = BrowserContextConfig(
	wait_for_network_idle_page_load_time=3.0,
)
browser = Browser()
context = BrowserContext(browser=browser, config=config)
#informacoes pessoais
password = os.getenv("PASSWORD")
vdi_api_key: str = os.getenv("VDI_API_KEY") # type: ignore
sensitive_data = {'x_name': "PEDRO_FERNANDES", 'x_password': password}


initial_actions = [
	{'open_tab': {'url': 'https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home'}},
	{"go_to_url":{"url":"https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home"}},
	{"input_text":{"index":2,"text":"PEDRO_FERNANDES"}},
	{"input_text":{"index":4,"text":password}},
	{"click_element":{"index":6}},
	
]
#20 23
llm= ChatOpenAI(
        base_url="https://genai-api-dev.dell.com/v1",
        model="llama-3-2-11b-vision-instruct",
        api_key=SecretStr(vdi_api_key),
        http_async_client=httpx.AsyncClient(verify=False),
        timeout=30
        
    )
agent = Agent(
		task=(
			"""0.in https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home
   			1. Click in the change objects page
      2. Enter change number pnr: PNR14551G
      3. Click in GO button
      4. check if the all the affected regions in the table are marked as Sucess"""
		),
		llm=llm,
		use_vision=False,
		max_failures=10,
		initial_actions=initial_actions,
		validate_output=False,
		browser_context=context,
		controller=controller,
		sensitive_data=sensitive_data
	)
async def main():

	history = await agent.run()
	history.model_thoughts()
	input('Press Enter to close...')
	await browser.close()

if __name__ == '__main__':
	asyncio.run(main())
