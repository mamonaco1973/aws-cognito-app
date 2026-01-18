# ================================================================================
# File: list.py
# ================================================================================
# Purpose:
#   Lambda handler for listing all notes in the Notes API.
#
# Updated Behavior:
#   - Derives owner from the Cognito JWT (access token) claim "sub"
#   - Queries DynamoDB by partition key (owner) to return only the caller's notes
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

def _get_owner(event: dict) -> str:
    """
    Extract the authenticated user identifier from the API Gateway HTTP API
    JWT authorizer context.

    Expected path (HTTP API v2 + JWT authorizer):
      event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
    """
    try:
        claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
        owner = str(claims.get("sub", "")).strip()
        if not owner:
            raise KeyError("sub claim missing")
        return owner
    except Exception:
        raise ValueError("Unauthorized: missing or invalid JWT claims")

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
    # Determine owner from JWT
    # --------------------------------------------------------------------------
    try:
        owner = _get_owner(event)
    except ValueError as exc:
        return _response(401, {"error": str(exc)})

    # --------------------------------------------------------------------------
    # Query notes for this owner
    # --------------------------------------------------------------------------
    try:
        resp = table.query(
            KeyConditionExpression=Key("owner").eq(owner)
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
