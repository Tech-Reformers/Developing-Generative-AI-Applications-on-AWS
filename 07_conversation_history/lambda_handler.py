"""Persistent conversation history with AWS Lambda + DynamoDB (reference).

This is the architecture from the slides: an API-Gateway-invoked Lambda that
keeps a per-user chat history in DynamoDB, so a conversation continues across
separate requests (unlike the in-memory chat in 03_converse).

Flow per request:
  1. Load the user's history from DynamoDB
  2. Append the new user message and store it
  3. Call Converse with the full history
  4. Store the assistant's reply and return it

NOTE: This file is a faithful reference of the slides - it expects a real
Lambda event (API Gateway + JWT authorizer) and the CONVERSATION_HISTORY_TABLE
environment variable, so it is not meant to run locally as-is. For a runnable
version, see chat_persistent.py, which simulates the same flow with a fixed
user_id and a real DynamoDB table.
"""
import os
import time

import boto3

bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")
dynamodb = boto3.resource("dynamodb")
conversation_table = dynamodb.Table(os.environ.get("CONVERSATION_HISTORY_TABLE"))
client = boto3.client("dynamodb")


def lambda_handler(event, context):
    # The authenticated user's ID comes from the JWT claims (Cognito authorizer)
    user_id = event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
    conversation_messages = get_conversation_history(user_id)

    # Append the incoming user message to the history and persist it
    user_msg = event["message"]
    conversation_messages.append({
        "role": "user",
        "content": [{"text": user_msg}],
    })
    store_message(user_id, user_msg, "user")

    # Call the model with the full conversation history
    model_response = bedrock_runtime.converse(
        modelId="amazon.nova-lite-v1:0",
        messages=conversation_messages,
        system=[{
            "text": "Please provide a helpful, conversational response based on "
                    "the available information and conversation history."
        }],
        inferenceConfig={"maxTokens": 300, "temperature": 0.7, "topP": 0.9},
    )

    # Persist the assistant's reply and return it
    assistant_msg = model_response["output"]["message"]["content"][0]["text"]
    store_message(user_id, assistant_msg, "assistant")

    return {
        "statusCode": 200,
        "body": assistant_msg,
    }


def store_message(user_id, message, role):
    now_in_seconds = time.time()
    expire_ttl = now_in_seconds + (30 * 24 * 60 * 60)  # 30 days

    conversation_table.put_item(Item={
        "userID": user_id,
        "timestamp": now_in_seconds,
        "message": message,
        "role": role,
        "ttl": expire_ttl,
    })


def get_conversation_history(user_id):
    paginator = client.get_paginator("query")
    pages = paginator.paginate(
        TableName=os.environ.get("CONVERSATION_HISTORY_TABLE"),
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
