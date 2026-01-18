# ================================================================================
# File: delete.py
# ================================================================================
# Purpose:
#   Lambda handler for deleting a note in the Notes API.
#
# Updated Behavior:
#   - Derives owner from the Cognito JWT (access token) claim "sub"
#   - Deletes only if the note belongs to the authenticated owner
#
# DynamoDB Schema:
#   PK: owner (string)
#   SK: id    (string, UUID)
#
# Expected Path:
#   DELETE /notes/{id}
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
    path_params = event.get("pathParameters") or {}
    note_id = str(path_params.get("id", "")).strip()
    if not note_id:
        raise ValueError("id path parameter is required")
    return note_id

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
    # Determine owner + note id
    # --------------------------------------------------------------------------
    try:
        owner  = _get_owner(event)
        note_id = _get_note_id(event)
    except ValueError as exc:
        # Unauthorized is 401; missing id is 400
        msg = str(exc)
        if msg.startswith("Unauthorized:"):
            return _response(401, {"error": msg})
        return _response(400, {"error": msg})

    # --------------------------------------------------------------------------
    # Delete item (scoped to owner)
    # --------------------------------------------------------------------------
    try:
        table.delete_item(
            Key={
                "owner": owner,
                "id": note_id
            }
        )
    except ClientError:
        return _response(500, {"error": "Failed to delete note"})

    # --------------------------------------------------------------------------
    # Success response
    # --------------------------------------------------------------------------
    return _response(200, {"deleted": True, "id": note_id})
