# ================================================================================
# File: update.py
# ================================================================================
# Purpose:
#   Lambda handler for updating an existing note by ID.
#
# Simplified Demo Behavior:
#   - Uses a fixed owner value ("global")
#   - Reads note ID from the request path
#   - Updates title and note fields in DynamoDB
#   - Updates updated_at timestamp
#   - Returns 404 if the note does not exist
#
# DynamoDB Schema:
#   PK: owner (string)
#   SK: id    (string, UUID)
#
# Expected Request Body:
#   {
#     "title": "Updated title",
#     "note":  "Updated note body"
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
    # Read note ID from path
    # --------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # Update item
    # --------------------------------------------------------------------------
    now = datetime.now(timezone.utc).isoformat()

    try:
        resp = table.update_item(
            Key={
                "owner": OWNER,
                "id":    note_id
            },
            UpdateExpression="SET #title = :title, #note = :note, #updated_at = :ts",
            ConditionExpression="attribute_exists(#id)",
            ExpressionAttributeNames={
                "#id":         "id",
                "#title":      "title",
                "#note":       "note",
                "#updated_at": "updated_at"
            },
            ExpressionAttributeValues={
                ":title": title,
                ":note":  note,
                ":ts":    now
            },
            ReturnValues="ALL_NEW"
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code == "ConditionalCheckFailedException":
            return _response(404, {"error": "Note not found"})
        return _response(500, {"error": "Failed to update note"})

    item = resp.get("Attributes", {})

    return _response(200, item)
