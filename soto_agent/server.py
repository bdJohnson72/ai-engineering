from fastapi import  FastAPI, HTTPException
from pydantic import BaseModel
import logging

from soto_agent.app import run_agent


class Request(BaseModel):
    question: str


app = FastAPI()
logger = logging.getLogger(__name__)

@app.post("/soto-agent")
def handle_soto_request(agent_request: Request) -> dict[str, str]:
    try:
        logger.info("sota agent reguest", agent_request)
        return {"answer" : run_agent(agent_request.question)}
    except Exception as e:
        logger.exception("agent loop failed")
        raise HTTPException(status_code=500, detail="There was an error")

