# ================================================================================
# File: list.py
# ================================================================================
# Purpose:
#   Lambda handler for listing all notes in the Notes API.
#
# Simplified Demo Behavior:
#   - Uses a fixed owner value ("global") for all notes
#   - Queries DynamoDB by partition key to return all notes
#
# DynamoDB Schema:
#   PK: owner (string)
#   SK: id    (string, UUID)
# ================================================================================

import json
import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# --------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------

TABLE_NAME = os.environ.get("NOTES_TABLE_NAME", "").strip()
OWNER      = "global"

dynamodb = boto3.resource("dynamodb")

# --------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------

def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }

def _require_env() -> None:
    if not TABLE_NAME:
        raise ValueError("NOTES_TABLE_NAME environment variable is required")

# --------------------------------------------------------------------------------
# Lambda Handler
# --------------------------------------------------------------------------------

def lambda_handler(event, context):
    # --------------------------------------------------------------------------
    # Validate environment
    # --------------------------------------------------------------------------
    try:
        _require_env()
        table = dynamodb.Table(TABLE_NAME)
    except ValueError as exc:
        return _response(500, {"error": str(exc)})

    # --------------------------------------------------------------------------
    # Query notes
    # --------------------------------------------------------------------------
    try:
        resp = table.query(
            KeyConditionExpression=Key("owner").eq(OWNER)
        )
    except ClientError:
        return _response(500, {"error": "Failed to list notes"})

    items = resp.get("Items", [])

    return _response(
        200,
        {
            "items": items
        }
    )
