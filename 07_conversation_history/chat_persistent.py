"""Persistent conversation chat - runnable local version of lambda_handler.py.

Same idea as the Lambda reference, but runs as an interactive terminal chat with
a fixed user_id and a real DynamoDB table. Because history lives in DynamoDB,
the conversation survives across restarts: quit, run it again, and the model
still remembers what you said earlier.

Usage:
    python chat_persistent.py            # chat (creates the table if needed)
    python chat_persistent.py --reset    # delete this user's history, then chat
    python chat_persistent.py --cleanup  # delete the whole table and exit
"""
import argparse
import sys
import time
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
MODEL_ID = "us.amazon.nova-lite-v1:0"
TABLE_NAME = "ConversationHistory"
USER_ID = "demo-user"  # stands in for the JWT 'sub' claim in the Lambda version

dynamodb = boto3.resource("dynamodb", region_name=REGION)
ddb_client = boto3.client("dynamodb", region_name=REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)


def get_or_create_table():
    existing = [t.name for t in dynamodb.tables.all()]
    if TABLE_NAME in existing:
        return dynamodb.Table(TABLE_NAME)
    print(f"Creating table '{TABLE_NAME}' ...")
    table = dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "userID", "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "userID", "AttributeType": "S"},
            {"AttributeName": "timestamp", "AttributeType": "N"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()
    return table


def store_message(table, user_id, message, role):
    now_in_seconds = Decimal(str(time.time()))  # Decimal for DynamoDB numbers
    expire_ttl = now_in_seconds + (30 * 24 * 60 * 60)  # 30 days
    table.put_item(Item={
        "userID": user_id,
        "timestamp": now_in_seconds,
        "message": message,
        "role": role,
        "ttl": expire_ttl,
    })


def get_conversation_history(user_id):
    paginator = ddb_client.get_paginator("query")
    pages = paginator.paginate(
        TableName=TABLE_NAME,
        KeyConditionExpression="userID = :val",
        ExpressionAttributeValues={":val": {"S": user_id}},
    )
    messages = []
    for page in pages:
        for item in page.get("Items", []):
            messages.append({
                "role": item["role"]["S"],
                "content": [{"text": item["message"]["S"]}],
            })
    return messages


def reset_history(table, user_id):
    """Delete all stored messages for this user."""
    resp = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("userID").eq(user_id)
    )
    with table.batch_writer() as batch:
        for item in resp.get("Items", []):
            batch.delete_item(Key={"userID": user_id, "timestamp": item["timestamp"]})
    print(f"Cleared history for {user_id}.")


def cleanup():
    try:
        dynamodb.Table(TABLE_NAME).delete()
        print(f"Deleting table '{TABLE_NAME}' ...")
    except ddb_client.exceptions.ResourceNotFoundException:
        print(f"Table '{TABLE_NAME}' not found (already gone).")


def chat(table):
    # Load whatever history already exists for this user (persisted from before)
    history = get_conversation_history(USER_ID)
    if history:
        print(f"Loaded {len(history)} message(s) from previous sessions.\n")
    print("Chat with Claude/Nova (history persists in DynamoDB). Type 'exit' to stop.\n")

    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in ("exit", "quit"):
            print("Goodbye! Your history is saved for next time.")
            break

        history.append({"role": "user", "content": [{"text": user_input}]})
        store_message(table, USER_ID, user_input, "user")

        response = bedrock_runtime.converse(
            modelId=MODEL_ID,
            messages=history,
            system=[{"text": "Please provide a helpful, conversational response "
                             "based on the conversation history."}],
            inferenceConfig={"maxTokens": 300, "temperature": 0.7, "topP": 0.9},
        )
        reply = response["output"]["message"]["content"][0]["text"]
        print(f"\nNova: {reply}\n")

        history.append({"role": "assistant", "content": [{"text": reply}]})
        store_message(table, USER_ID, reply, "assistant")


def main():
    parser = argparse.ArgumentParser(description="Persistent DynamoDB-backed chat.")
    parser.add_argument("--reset", action="store_true",
                        help="Clear this user's history before chatting.")
    parser.add_argument("--cleanup", action="store_true",
                        help="Delete the whole table and exit.")
    args = parser.parse_args()

    try:
        if args.cleanup:
            cleanup()
            return 0
        table = get_or_create_table()
        if args.reset:
            reset_history(table, USER_ID)
        chat(table)
        return 0
    except ClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
