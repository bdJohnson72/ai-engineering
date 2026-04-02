"""Tool functions for the LLM tool calling demo.

Each function represents a "tool" that an LLM can invoke:
- get_account: Query Salesforce for Account details
- query_orders: Query local SQLite database for order history
- create_task: Create a Task record in Salesforce
"""

import logging
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from simple_salesforce import Salesforce

load_dotenv()
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "products.db"


def _get_sf_client() -> Salesforce:
    """Create an authenticated Salesforce client from environment variables."""
    return Salesforce(
        username=os.environ["SF_USERNAME"],
        password=os.environ["SF_PASSWORD"],
        security_token=os.environ["SF_SECURITY_TOKEN"],
    )


def get_account(account_name: str) -> dict:
    """Look up a Salesforce Account by name.

    Args:
        account_name: Full or partial account name to search for.

    Returns:
        Dict with account details (name, industry, phone, billing_city)
        or an error message if not found.
    """
    sf = _get_sf_client()
    result = sf.query(
        f"SELECT Name, Industry, Phone, BillingCity, BillingState, Website "
        f"FROM Account "
        f"WHERE Name LIKE '%{account_name}%' "
        f"LIMIT 5"
    )

    if result["totalSize"] == 0:
        return {"error": f"No account found matching '{account_name}'"}

    accounts = []
    for record in result["records"]:
        accounts.append({
            "name": record["Name"],
            "industry": record.get("Industry"),
            "phone": record.get("Phone"),
            "billing_city": record.get("BillingCity"),
            "billing_state": record.get("BillingState"),
            "website": record.get("Website"),
        })

    return {"accounts": accounts, "count": len(accounts)}


def query_orders(account_name: str) -> list[dict]:
    """Query order history for an account from the local SQLite database.

    Args:
        account_name: Account name to look up orders for.

    Returns:
        List of order dicts (product, quantity, date) or empty list if none found.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT o.order_id, o.product_name, o.quantity_cases, o.order_date,
               p.category, p.brand_family
        FROM orders o
        JOIN products p ON o.product_name = p.product_name
        WHERE o.account_name LIKE ?
        ORDER BY o.order_date DESC
        """,
        (f"%{account_name}%",),
    )

    orders = [dict(row) for row in cur.fetchall()]
    conn.close()

    logger.info("Found %d orders for '%s'", len(orders), account_name)
    return orders


def create_task(account_name: str, subject: str, description: str) -> dict:
    """Create a Task record linked to an Account in Salesforce.

    Args:
        account_name: Account name to link the task to.
        subject: Task subject line.
        description: Task description/body.

    Returns:
        Dict with the created task ID and status, or an error message.
    """
    sf = _get_sf_client()

    # Find the Account ID first
    result = sf.query(
        f"SELECT Id, Name FROM Account WHERE Name LIKE '%{account_name}%' LIMIT 1"
    )

    if result["totalSize"] == 0:
        return {"error": f"No account found matching '{account_name}'"}

    account_id = result["records"][0]["Id"]
    account_name_actual = result["records"][0]["Name"]

    task = sf.Task.create({
        "Subject": subject,
        "Description": description,
        "WhatId": account_id,
        "Status": "Not Started",
        "Priority": "Normal",
    })

    logger.info("Created Task %s on Account '%s'", task["id"], account_name_actual)
    return {
        "task_id": task["id"],
        "account": account_name_actual,
        "subject": subject,
        "status": "Not Started",
    }
