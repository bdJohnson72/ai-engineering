import logging
import os

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from soto_agent.app import run_agent


SOTO_API_KEY = os.environ.get("SOTO_API_KEY")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided: str | None = Security(_api_key_header)) -> str:
    if not SOTO_API_KEY:
        raise HTTPException(status_code=503, detail="server missing SOTO_API_KEY")
    if provided != SOTO_API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")
    return provided


class Request(BaseModel):
    question: str


app = FastAPI()
logger = logging.getLogger(__name__)


@app.post("/soto-agent")
def handle_soto_request(
    agent_request: Request,
    _: str = Depends(require_api_key),
) -> dict[str, str]:
    try:
        logger.info("sota agent reguest", agent_request)
        return {"answer": run_agent(agent_request.question)}
    except Exception:
        logger.exception("agent loop failed")
        raise HTTPException(status_code=500, detail="There was an error")
