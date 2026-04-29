from openai import OpenAI
from dotenv import load_dotenv
from chromadb import PersistentClient
from litellm import completion
from pydantic import BaseModel, Field
from pathlib import Path
from tenacity import retry, wait_exponential
from ingest import Result, DB_NAME, EMBEDDING_MODEL, COLLECTION_NAME

load_dotenv(override=True)
OPEN_AI_MODEL = "gpt-4.1-nano"
RETRIEVAL_K = 10

vectorstore = PersistentClient(path=DB_NAME)
collection = vectorstore.get_or_create_collection(COLLECTION_NAME)
openAI = OpenAI()

SYSTEM_PROMPT = """
    You are a helpful assistant at the Boston Beer Company, trained as a data analyst to help users with questions
    related to the industry. This includes beer, malted beverages like Twisted Tea or Truly, and the premium RTD category
    like Sun Cruiser. You have access to the company's beer intelligence database. Your response will be evaluated for accuracy, relevance and completeness.
    You should only answer the question. If you do not know the answer say so. For context here are specific extracts from the knowledge base
    that might be relevant to the user's question.
    {context}
    With this context, please answer the user's question. Be accurate, relevant and complete.
"""


def fetch_content(question: str) -> list[Result]:
    # embed question
    query_vec = openAI.embeddings.create(model=EMBEDDING_MODEL,
                                         input=[question]).data[0].embedding
    # query chroma
    results = collection.query(query_embeddings=[query_vec], n_results=RETRIEVAL_K) #results in a dict
    print(f"A sample results is {results["documents"][0][0]} and {results["metadatas"][0][0]}")
    # zip docs and metas
    chunks = []
    for result in zip(results["documents"][0], results['metadatas'][0]):
        chunks.append(Result(page_content=result[0], metadata=result[1]))
    # wrap in result
    # return
    return chunks

def make_rag_messages(question: str, history: list[dict], chunks: list[Result]) -> list[dict]:
    context = "\n\n".join(
        f"Extract from {chunk.metadata['source']}:\n{chunk.page_content}" for chunk in chunks
    )
    system_prompt = SYSTEM_PROMPT.format(context=context)
    return (
            [{"role": "system", "content": system_prompt}]
            + history
            + [{"role": "user", "content": question}]
    )

def answer_question(question: str, history: list[dict] = []) -> tuple[str, list[Result]]:
    chunks = fetch_content(question)
    messages = make_rag_messages(question, history, chunks)
    response = openAI.chat.completions.create(model=OPEN_AI_MODEL, messages=messages)
    answer = response.choices[0].message.content
    return  answer, chunks



if __name__ == "__main__":
    answer, chunks = answer_question("How can Sam Adams boost sales in 2026")
    print(f"--- ANSWER ---")
    print(answer)
    print(f"\n--- {len(chunks)} CHUNKS USED ---")
    for c in chunks:
        print(f"- {c.metadata['source']}")