import json
import logging
import os

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from soto_agent.app import run_agent
from soto_agent.sf_publish import publish_status


SOTO_API_KEY = os.environ.get("SOTO_API_KEY")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided: str | None = Security(_api_key_header)) -> str:
    if not SOTO_API_KEY:
        raise HTTPException(status_code=503, detail="server missing SOTO_API_KEY")
    if provided != SOTO_API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")
    return provided


class Request(BaseModel):
    query: str
    correlationId: str | None = None
    accountId: str | None = None
    iStoreNumber: str | None = None
    accountName: str | None = None


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = FastAPI()
logger = logging.getLogger(__name__)


@app.post("/soto-agent")
def handle_soto_request(
    agent_request: Request,
    _: str = Depends(require_api_key),
) -> dict[str, str]:
    correlation_id = agent_request.correlationId
    try:
        logger.info("soto agent request: %s", agent_request.model_dump(exclude_none=True))
        answer = run_agent(agent_request.query)
        if correlation_id:
            publish_status(correlation_id, "SUCCESS", result=json.dumps({"answer": answer}))
        return {"answer": answer}
    except Exception as e:
        logger.exception("agent loop failed")
        if correlation_id:
            publish_status(correlation_id, "ERROR", message=str(e))
        raise HTTPException(status_code=500, detail="There was an error")
