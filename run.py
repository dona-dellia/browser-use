import os
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
#controle
from prism_configs.prism_controller import controller
#browser
from prism_configs.prism_browser import browser,context
from prism_configs.prism_prompts import glossary
#informacoes pessoais
password = os.getenv("PASSWORD")
vdi_api_key: str = os.getenv("VDI_API_KEY") # type: ignore
sensitive_data = {'x_name': "R_Rodrigues", 'x_password': password}


initial_actions = [
	{'open_tab': {'url': 'https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home'}},
	{"go_to_url":{"url":"https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home"}},
	{"input_text":{"index":2,"text":"R_Rodrigues"}},
	{"input_text":{"index":4,"text":password}},
	{"click_element":{"index":6}},
 # change objects task
	# {"click_element":{"index":4}},
	# {"click_element":{"index":27}},
	# {"scroll_down_element":{"pixels":200,"index":0}},
]
#20 23
llm= ChatOpenAI(
        base_url="https://genai-api-dev.dell.com/v1",
        model="llama-3-3-70b-instruct",
        api_key=SecretStr(vdi_api_key),
        http_async_client=httpx.AsyncClient(verify=False),
        timeout=30
        
    )

# TODO
# 1. Alterar system prompt para a11y
# 2. TSI pegar dados da API
# 3. Melhorar avaliação ou adicionar juiz
# 4. Adicionar parametros de scroll/scrollable na a11y

agent = Agent(
		task=("""
            GIVEN a user fills fields(Change Object Type, with only ECO, status with only Success, Regions Affected with only DAO AND EMEA) on the Change Object page WHEN he clicks the 'RESET' button THEN all fields in the form are cleared
            """),
		llm=llm,
		use_vision=False,
		max_failures=10,
		initial_actions=initial_actions,
		validate_output=False,
		browser_context=context,
		controller=controller,
		sensitive_data=sensitive_data,
        save_conversation_path="output/scroll_element",
        message_context=glossary,
        save_images_path="output"
	)
async def main():

    history = await agent.run(max_steps=10)
    history.model_thoughts()
    input('Press Enter to close...')
    await context.close()
    await browser.close()

if __name__ == '__main__':
	asyncio.run(main())