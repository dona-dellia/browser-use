from agno.models.openai import OpenAIChat
import httpx
import os
from dotenv import load_dotenv
load_dotenv()

vdi_api_key: str = os.getenv("VDI_API_KEY") # type: ignore

model = OpenAIChat(
        base_url="https://genai-api-dev.dell.com/v1",
        http_client=httpx.Client(verify=False),
        id="llama-3-3-70b-instruct",
        api_key=vdi_api_key,
        
    )