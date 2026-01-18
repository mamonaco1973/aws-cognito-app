# ================================================================================
# File: get.py
# ================================================================================
# Purpose:
#   Lambda handler for retrieving a single note by ID.
#
# Updated Behavior:
#   - Derives owner from the Cognito JWT (access token) claim "sub"
#   - Reads note ID from the request path
#   - Retrieves the note scoped to the authenticated owner
#   - Returns 404 if the note does not exist or does not belong to the caller
#
# DynamoDB Schema:
#   PK: owner (string)
#   SK: id    (string, UUID)
# ================================================================================

import json
import os

import boto3
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

def _get_note_id(event: dict) -> str:
    try:
        return (
            event
            .get("pathParameters", {})
            .get("id", "")
            .strip()
        )
    except AttributeError:
        return ""

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
    # Determine owner
    # --------------------------------------------------------------------------
    try:
        owner = _get_owner(event)
    except ValueError as exc:
        return _response(401, {"error": str(exc)})

    # --------------------------------------------------------------------------
    # Read note ID from path
    # --------------------------------------------------------------------------
    note_id = _get_note_id(event)

    if not note_id:
        return _response(400, {"error": "Note id is required"})

    # --------------------------------------------------------------------------
    # Fetch item (scoped to owner)
    # --------------------------------------------------------------------------
    try:
        resp = table.get_item(
            Key={
                "owner": owner,
                "id":    note_id
            }
        )
    except ClientError:
        return _response(500, {"error": "Failed to retrieve note"})

    item = resp.get("Item")

    if not item:
        # Either not found OR not owned by caller
        return _response(404, {"error": "Note not found"})

    return _response(200, item)
