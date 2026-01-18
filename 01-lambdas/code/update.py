# ================================================================================
# File: update.py
# ================================================================================
# Purpose:
#   Lambda handler for updating an existing note.
#
# Updated Behavior:
#   - Derives owner from the Cognito JWT (access token) claim "sub"
#   - Reads note ID from request path
#   - Updates only if the note belongs to the authenticated owner
#
# DynamoDB Schema:
#   PK: owner (string)
#   SK: id    (string, UUID)
#
# Expected Request Body:
#   {
#     "title": "Updated title",
#     "note":  "Updated body"
#   }
# ================================================================================

import json
import os
from datetime import datetime, timezone

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
    Extract authenticated user identifier from JWT.
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
    # Determine owner + note id
    # --------------------------------------------------------------------------
    try:
        owner = _get_owner(event)
    except ValueError as exc:
        return _response(401, {"error": str(exc)})

    note_id = _get_note_id(event)
    if not note_id:
        return _response(400, {"error": "Note id is required"})

    # --------------------------------------------------------------------------
    # Parse request body
    # --------------------------------------------------------------------------
    try:
        payload = json.loads(event.get("body", "{}"))
        title   = str(payload.get("title", "")).strip()
        note    = str(payload.get("note", "")).strip()

        if not title:
            raise ValueError("title is required")
        if not note:
            raise ValueError("note is required")

    except (ValueError, json.JSONDecodeError) as exc:
        return _response(400, {"error": f"Invalid request body: {str(exc)}"})

    now = datetime.now(timezone.utc).isoformat()

    # --------------------------------------------------------------------------
    # Update item (owner-scoped)
    # --------------------------------------------------------------------------
    try:
        table.update_item(
            Key={
                "owner": owner,
                "id": note_id
            },
            UpdateExpression="""
                SET
                  #title = :title,
                  #note  = :note,
                  updated_at = :updated
            """,
            ExpressionAttributeNames={
                "#title": "title",
                "#note":  "note"
            },
            ExpressionAttributeValues={
                ":title":   title,
                ":note":    note,
                ":updated": now
            },
            ConditionExpression="attribute_exists(id)"
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            # Either not found OR not owned by caller
            return _response(404, {"error": "Note not found"})
        return _response(500, {"error": "Failed to update note"})

    # --------------------------------------------------------------------------
    # Success response
    # --------------------------------------------------------------------------
    return _response(
        200,
        {
            "id": note_id,
            "title": title,
            "note": note
        }
    )
