"""Question answering over a document stored in Amazon S3.

Same idea as qa_document.py, but instead of sending the file bytes inline, we
point Converse at the document in S3 via an `s3Location`. This is the better
choice for large documents - you don't ship the bytes through your app.

This script is self-contained: it creates a bucket, uploads the sample PDF,
runs the question, and can tear the bucket down again.

Usage:
    python qa_s3.py            # create bucket, upload PDF, ask the question
    python qa_s3.py --cleanup  # empty and delete the bucket
"""
import argparse
import sys

import boto3
from botocore.exceptions import ClientError

# Use the region configured in your AWS CLI/profile (falls back to us-east-1).
REGION = boto3.session.Session().region_name or "us-east-1"
MODEL_ID = "us.amazon.nova-2-lite-v1:0"
PDF_FILE = "sample_report.pdf"
S3_KEY = "documents/sample_report.pdf"


def account_id():
    return boto3.client("sts").get_caller_identity()["Account"]


def bucket_name():
    return f"bedrock-qa-demo-{account_id()}"


def run():
    acct = account_id()
    bucket = bucket_name()
    s3 = boto3.client("s3")
    client = boto3.client("bedrock-runtime")

    # 1. Create the bucket (idempotent) and upload the document.
    # us-east-1 rejects a LocationConstraint; every other region requires one
    # that matches the endpoint the request is sent to.
    try:
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=bucket)
        else:
            s3.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={"LocationConstraint": REGION},
            )
        print(f"Created bucket: {bucket} ({REGION})")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"Bucket already exists: {bucket}")
    s3.upload_file(PDF_FILE, bucket, S3_KEY)
    print(f"Uploaded {PDF_FILE} to s3://{bucket}/{S3_KEY}")

    # 2. Reference the S3 document in a Converse message
    messages = [{
        "role": "user",
        "content": [
            {
                "document": {
                    "format": "pdf",
                    "name": "QuantumReport",
                    "source": {
                        "s3Location": {
                            "uri": f"s3://{bucket}/{S3_KEY}",
                            "bucketOwner": acct,
                        }
                    },
                }
            },
            {"text": "Describe the following document and list the leading vendors."},
        ],
    }]

    response = client.converse(
        modelId=MODEL_ID,
        messages=messages,
        inferenceConfig={"maxTokens": 300, "topP": 0.1, "temperature": 0.3},
    )
    print("\n[Response]")
    print(response["output"]["message"]["content"][0]["text"])
    print(f"\nDone. Run 'python qa_s3.py --cleanup' to delete the bucket.")


def cleanup():
    bucket = bucket_name()
    s3 = boto3.resource("s3")
    try:
        b = s3.Bucket(bucket)
        b.objects.all().delete()
        b.delete()
        print(f"Deleted bucket: {bucket}")
    except s3.meta.client.exceptions.NoSuchBucket:
        print(f"Bucket not found (already gone): {bucket}")


def main():
    parser = argparse.ArgumentParser(description="QA over an S3 document with Converse.")
    parser.add_argument("--cleanup", action="store_true",
                        help="Delete the demo bucket instead of running the query.")
    args = parser.parse_args()
    try:
        cleanup() if args.cleanup else run()
        return 0
    except ClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
