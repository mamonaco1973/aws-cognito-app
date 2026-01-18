# ================================================================================
# File: create.py
# ================================================================================
# Purpose:
#   Lambda handler for creating a new note in the Notes API.
#
# Simplified v1 Behavior:
#   - Uses a fixed owner value ("global") for all notes
#   - Generates a UUID for the note ID
#   - Stores the note in DynamoDB
#   - Returns the created note
#
# DynamoDB Schema:
#   PK: owner (string)
#   SK: id    (string, UUID)
#
# Expected Request Body:
#   {
#     "title": "Note title",
#     "note":  "Note body"
#   }
# ================================================================================

import json
import os
import uuid
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
    # Build item
    # --------------------------------------------------------------------------
    note_id = str(uuid.uuid4())
    now     = datetime.now(timezone.utc).isoformat()

    item = {
        "owner":      OWNER,
        "id":         note_id,
        "title":      title,
        "note":       note,
        "created_at": now,
        "updated_at": now
    }

    # --------------------------------------------------------------------------
    # Persist item
    # --------------------------------------------------------------------------
    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(#id)",
            ExpressionAttributeNames={"#id": "id"}
        )
    except ClientError:
        return _response(500, {"error": "Failed to create note"})

    # --------------------------------------------------------------------------
    # Success response
    # --------------------------------------------------------------------------
    return _response(
        201,
        {
            "id":    note_id,
            "title": title,
            "note":  note
        }
    )
