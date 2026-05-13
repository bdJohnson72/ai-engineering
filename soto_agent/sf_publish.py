import logging
import os

import requests

SF_API_VERSION = "v63.0"
PE_OBJECT = "Account_Intelligence__e"

logger = logging.getLogger(__name__)


def _get_required_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"missing required env var: {key}")
    return value


def _get_sf_token() -> tuple[str, str]:
    instance_url = _get_required_env("SF_INSTANCE_URL")
    resp = requests.post(
        f"{instance_url}/services/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": _get_required_env("SF_CLIENT_ID"),
            "client_secret": _get_required_env("SF_CLIENT_SECRET"),
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"], instance_url


def publish_status(correlation_id: str, status: str, result: str | None = None, message: str | None = None) -> None:
    """Publish Account_Intelligence__e PE. Best-effort — logs and swallows errors."""
    try:
        token, instance_url = _get_sf_token()
        payload: dict[str, str] = {"CorrelationId__c": correlation_id, "Status__c": status}
        if result is not None:
            payload["Result__c"] = result
        if message is not None:
            payload["Message__c"] = message

        resp = requests.post(
            f"{instance_url}/services/data/{SF_API_VERSION}/sobjects/{PE_OBJECT}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=10,
        )
        if resp.status_code not in (200, 201):
            logger.error("PE publish failed: %s %s", resp.status_code, resp.text)
        else:
            logger.info("PE published: corr=%s status=%s", correlation_id, status)
    except Exception:
        logger.exception("PE publish raised — swallowing to keep agent loop alive")
