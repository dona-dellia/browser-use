import os
import httpx
from pydantic import SecretStr
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Carrega variáveis de ambiente
load_dotenv()

# Instancia o LLM
llm = ChatOpenAI(
    base_url="https://genai-api-dev.dell.com/v1",
    model="llama-3-3-70b-instruct",
    api_key=SecretStr(os.getenv("VDI_API_KEY")),
    http_client=httpx.Client(verify=False),
    timeout=30
)

human_template = f"{{question}}"
prompt_template = ChatPromptTemplate.from_messages(
    [
        MessagesPlaceholder(variable_name="history"),
        ("human", human_template),
    ]
)
chain = prompt_template | llm

store = {}

def get_by_session_id(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

chain_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history= get_by_session_id,
    input_messages_key="question",
    history_messages_key="history",
)

for i in range(3):
    user_question = input(">>>>")
    result = chain_with_history.invoke(
        {"question": user_question},
        config={"configurable": {"session_id": "foo"}},
    )
    print(result.content)
    
print(store.get("foo"))


