"""Generate synthetic city reviews with varying sentiment using Amazon Nova Lite,
and store them in DynamoDB as a labeled dataset.

For each city we pick a sentiment (positive / negative / neutral), build a prompt
for that sentiment, have Nova write a review, and save it to a DynamoDB table.
The result is a set of reviews with known sentiment/ratings - handy test data
for a sentiment classifier.

Usage:
    python generate_reviews.py            # create table, generate reviews, store them
    python generate_reviews.py --cleanup  # delete the table when you're done
"""
import argparse
import json
import random
import sys
import uuid
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# Trimmed to 3 cities and shorter reviews so the demo runs quickly in class
CITIES = ["Denver", "Seattle", "Austin"]

MODEL_ID = "amazon.nova-lite-v1:0"
TABLE_NAME = "synthetic-reviews"
REGION = "us-east-1"


def generate_sentiment_distribution():
    """Assign a sentiment to each city (biased toward positive, like real reviews)."""
    sentiments = ["positive", "negative", "neutral"]
    weights = [0.6, 0.2, 0.2]
    return random.choices(sentiments, weights=weights, k=len(CITIES))


def generate_review_prompt(city, sentiment):
    """Return a prompt for the requested sentiment, plus a matching star rating."""
    if sentiment == "positive":
        prompts = [
            f"Write an enthusiastic 4- or 5-star review of {city}. Focus on the "
            f"food scene, culture, and attractions. Be specific. About 150 words.",
            f"Write a glowing review of {city} - great neighborhoods, friendly "
            f"people, excellent dining. Personal and positive. About 150 words.",
        ]
        rating = random.choice([4, 4, 5])  # more 4s than 5s
    elif sentiment == "negative":
        prompts = [
            f"Write a disappointed 1- or 2-star review of {city}. Focus on cost, "
            f"traffic, weather, or crowds. Specific and honest. About 150 words.",
            f"Write a critical review of {city} - overrated attractions, poor "
            f"value, daily annoyances. About 150 words.",
        ]
        rating = random.choice([1, 2, 2])
    else:  # neutral
        prompts = [
            f"Write a balanced 3-star review of {city} weighing good and bad "
            f"evenly. Some highlights, some drawbacks. About 150 words.",
            f"Write an even-handed review of {city} - ups and downs, neither rave "
            f"nor rant. About 150 words.",
        ]
        rating = 3

    return random.choice(prompts), rating


def call_nova(prompt, bedrock_client, model_id=MODEL_ID):
    """Call Amazon Nova Lite to generate a review."""
    # Define the message with proper Nova Lite format
    message_list = [{"role": "user", "content": [{"text": prompt}]}]

    # Configure inference parameters
    inf_params = {"maxTokens": 400, "temperature": 0.7}

    body = {
        "schemaVersion": "messages-v1",
        "messages": message_list,
        "inferenceConfig": inf_params,
    }

    # Invoke Amazon Nova Lite with Amazon Bedrock
    response = bedrock_client.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
    )

    # Extract response body
    response_body = json.loads(response["body"].read())

    # Return content from response body
    return response_body["output"]["message"]["content"][0]["text"]


def get_or_create_table(dynamodb):
    """Return the reviews table, creating it (on-demand billing) if needed."""
    existing = [t.name for t in dynamodb.tables.all()]
    if TABLE_NAME in existing:
        return dynamodb.Table(TABLE_NAME)

    print(f"Creating table '{TABLE_NAME}' ...")
    table = dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[{"AttributeName": "review_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "review_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",  # no capacity planning for a demo
    )
    table.wait_until_exists()
    return table


def upload_to_dynamodb(table, review_text, rating, city, sentiment):
    """Store one review row. Returns the generated review_id."""
    review_id = str(uuid.uuid4())
    table.put_item(Item={
        "review_id": review_id,
        "city": city,
        "sentiment": sentiment,
        "rating": Decimal(rating),  # DynamoDB stores numbers as Decimal
        "review_text": review_text,
    })
    return review_id


def delete_table():
    """Delete the reviews table (cleanup)."""
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)
    try:
        table.delete()
        table.wait_until_not_exists()
        print(f"Deleted table '{TABLE_NAME}'.")
    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        print(f"Table '{TABLE_NAME}' does not exist - nothing to delete.")


def run():
    bedrock_client = boto3.client("bedrock-runtime", region_name=REGION)
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = get_or_create_table(dynamodb)

    # Generate sentiment distribution across the cities
    sentiments = generate_sentiment_distribution()

    # Process each city
    for i, city in enumerate(CITIES):
        print(f"\nProcessing {i + 1}: {city} ({sentiments[i]})")

        # Generate prompt and rating
        prompt, rating = generate_review_prompt(city, sentiments[i])

        # Call Amazon Nova to generate a review
        review_text = call_nova(prompt, bedrock_client)

        if review_text:
            # Upload to DynamoDB
            review_id = upload_to_dynamodb(
                table, review_text, rating, city, sentiments[i]
            )
            print(f"Stored review {review_id} ({rating} stars)")
            print(review_text)

    print(f"\nDone. Reviews stored in table '{TABLE_NAME}'.")
    print("Run 'python generate_reviews.py --cleanup' to delete the table.")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic reviews with Nova Lite.")
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete the DynamoDB table and exit (no reviews generated).",
    )
    args = parser.parse_args()

    try:
        if args.cleanup:
            delete_table()
        else:
            run()
        return 0
    except ClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
