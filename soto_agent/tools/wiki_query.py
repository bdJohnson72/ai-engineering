from pydantic import BaseModel, Field
import os
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv



load_dotenv()

SELECT_PAGES_SYSTEM_PROMPT = """
    You are a an expert Sales Analyst in the beer and beyond beer industry. When a user asks you a question you 
    should search index to find the top 8 pages most likely to be relevant to their question. If you can not find anything you 
    should say that. Return the reletive paths exactly as they appear in the index. 
"""


_client = AzureOpenAI(
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"]
)

_deployment = os.environ["AZURE_OPENAI_DEPLOYMENT_CHAT"]

VAULT_PATH = Path(os.getenv("VAULT_PATH", str(Path.home() / "Documents/Obsidian Vault/Notes")))

def _load_index() -> str:
    with open(VAULT_PATH / "index.md") as f:
        return f.read()

class PageSelection(BaseModel):
    pages: list[str]

class WikiAnswer(BaseModel):
    answer: str
    consulted: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)

def wiki_query(question: str) -> WikiAnswer:
    pass

def _select_pages(question: str, index_text: str) -> list[str]:
    response = _client.chat.completions.parse(model=_deployment, messages=[
        {"role": "system", "content": SELECT_PAGES_SYSTEM_PROMPT},
        {"role": "user", "content": f"What strategy should I use to sell Sun Cruiser in an On Premise store {index_text}"}


    ], response_format=PageSelection)
    return response.choices[0].message.parsed.pages



