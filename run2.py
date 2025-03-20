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

password = os.getenv("PASSWORD")
vdi_api_key: str = os.getenv("VDI_API_KEY") # type: ignore


llm= ChatOpenAI(
        base_url="https://genai-api-dev.dell.com/v1",
        model="llama-3-2-11b-vision-instruct",
        api_key=SecretStr(vdi_api_key),
        http_async_client=httpx.AsyncClient(verify=False),
        
    )
agent = Agent(
		task=(
			"""
 open tab 'https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home', wait 3 seconds then access 'https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home'

then type on username Julia_Menezes  and on password type RA45-GT87a wait 1 second and click on go.

   US ID: CMBM-2410
    US TITLE: 
UIP DEC: PRISM CM Adapter - ECO Processing with Deviation Reversal - Add WD value to Change Order Live Que Totals and Search Dropdown Menus
    US DESCRIPTION: 
As a PRISM CM Adapter Delivery team, we want to update the ECO process to accept a Y status from the API and display a WD status to the UI if the ECO passes validation.

    ACCEPTANCE CRITERIA:
GIVEN a user on the Change Objects landing page (url: https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/change-objects/search)
WHEN the user views the Live Que Totals widget (StaticText 'Live Queue Totals')
THEN the WD value should be displayed in the widget with the total number of ECOs at WD status.

GIVEN a user on the Change Objects landing page (url: https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/change-objects/search)
WHEN the user selects to search by the STATUS field (combobox 'Status All')
THEN the WD status should be available as a search criteria (combobox 'Status All') and displayed in the search results.
```

   """
		),
		llm=llm,
		use_vision=False
  ,
		max_failures=10,
        generate_gif=True,
		validate_output=False,
	)
async def main():

	history = await agent.run()
	history.model_thoughts()
	input('Press Enter to close...')


if __name__ == '__main__':
	asyncio.run(main())
