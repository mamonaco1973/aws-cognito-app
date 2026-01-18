# ================================================================================
# File: delete.py
# ================================================================================
# Purpose:
#   Lambda handler for deleting a note by ID.
#
# Simplified Demo Behavior:
#   - Uses a fixed owner value ("global")
#   - Reads note ID from the request path
#   - Deletes the note from DynamoDB
#   - Returns 404 if the note does not exist
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
    # Delete item
    # --------------------------------------------------------------------------
    try:
        table.delete_item(
            Key={
                "owner": OWNER,
                "id":    note_id
            },
            ConditionExpression="attribute_exists(#id)",
            ExpressionAttributeNames={
                "#id": "id"
            }
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code == "ConditionalCheckFailedException":
            return _response(404, {"error": "Note not found"})
        return _response(500, {"error": "Failed to delete note"})

    return _response(
        200,
        {"message": "Note deleted"}
    )
