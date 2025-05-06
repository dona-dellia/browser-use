from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.messages.utils import convert_to_openai_messages
from langchain_openai import ChatOpenAI
from mem0 import Memory as Mem0Memory
from mem0.llms import openai as mem0_openai
from pydantic import SecretStr
import httpx
import os

load_dotenv()
os.environ["MEM0_TELEMETRY"] = "False"
vdi_api_key: str = os.getenv("VDI_API_KEY") # type: ignore

# Setup da LLM
llm = ChatOpenAI(
    base_url="https://genai-api-dev.dell.com/v1",
    model="llama-3-3-70b-instruct",
    api_key=SecretStr(vdi_api_key),
    http_async_client=httpx.AsyncClient(verify=False),
    timeout=30,
)
# :warning: Não passamos llm_instance no config do Mem0, apenas usamos para mensagens e embedder config
# :gear: Passamos apenas os campos permitidos explicitamente para o Mem0Memory
mem0 = Mem0Memory.from_config(
    config_dict={
        "agent_id": "dell_test_agent",
        "embedder_provider": "openai",  # Dell compatível com OpenAI API
        "embedder_model": "gte-large",  # ou o modelo correto da Dell
        "embedder_dims": 1024,  # dim do modelo de embedding da Dell
        "vector_store": {
            "normalize_l2": True,
            "path": "/tmp/mem0_dell_test",
            "collection_name": "default",
            "distance_strategy": "cosine"
        }
    }
)
# Mensagens simuladas
messages = [
    HumanMessage(content="Qual a diferença entre RAM e SSD?"),
    HumanMessage(content="E qual devo priorizar para performance?")
]

parsed = convert_to_openai_messages(messages)
# Testa o add
result = mem0.add(
    messages=parsed,
    agent_id="dell_test_agent",
    memory_type="procedural_memory",
    metadata={"step": 1},
    llm=llm
    
)
print("Resultado do .add():")
print(result)