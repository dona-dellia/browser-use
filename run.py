import os
import sys
from pathlib import Path

import httpx
from pydantic import BaseModel, Field, SecretStr
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio

from langchain_groq import ChatGroq

from browser_use import Agent, Controller, ActionResult, Browser
from browser_use.browser.context import BrowserContext
from langchain.output_parsers import PydanticOutputParser
from dotenv import load_dotenv
from browser_use.browser.context import BrowserContextConfig
logger = logging.getLogger(__name__)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

load_dotenv()

CONVERSATION_PATH = "./verification/"
ENRICHMENT = ["raw", "ideal" "E1"]

#controle
controller = Controller(exclude_actions=['search_google'])

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

controller = Controller(exclude_actions=['search_google'])

#browser
config = BrowserContextConfig(
	wait_for_network_idle_page_load_time=3.0,
)
browser = Browser()
context = BrowserContext(browser=browser, config=config)
#informacoes pessoais
#password = os.getenv("PASSWORD")
#vdi_api_key: str = os.getenv("VDI_API_KEY") # type: ignore
#sensitive_data = {'x_name': "R_RODRIGUES", 'x_password': password}


initial_actions = [
	{'open_tab': {'url': 'https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home'}},
	{"go_to_url":{"url":"https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home"}},
	{"input_text":{"index":2,"text":"R_RODRIGUES"}},
	#{"input_text":{"index":4,"text":password}},
	#{"click_element":{"index":6}},
	
]
     
def us_executor(us, path):
    llm = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile")

    agent = Agent(
            task=(us),
            llm=llm,
            use_vision=False,
            max_failures=10,
            #initial_actions=initial_actions,
            validate_output=False,
            browser_context=context,
            controller=controller,
            #sensitive_data=sensitive_data,
            save_conversation_path=path
        )
    return agent


async def us_executor_by_ids():
     """
     """
     US_max = 10
     for i in range(1,US_max+1,1):
        for type in ENRICHMENT:
            await us_executor_by_id_type(i, type)
     

async def us_executor_by_id_type(us_id, type):
    """
    
    """
    us_task = ''
    us_id = str(us_id)
    PATH = './verification/US/'
    path_log = PATH+us_id+"/"+type+"/log/"
    path_file = PATH+us_id+"/"+type+"/"+type+".txt"
    
    with open(path_file, 'r') as file:
            us_task = file.read()
    
    us_text = us_task

    agent =  us_executor(us_text, path_log)
    history = await agent.run()
	#history.model_thoughts()
    history.final_result()

    await browser.close()
     
async def main():
     """
     Execute for all USs
     """
     await us_executor_by_ids()


if __name__ == '__main__':
	asyncio.run(main())
