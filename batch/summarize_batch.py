"""Create a Bedrock batch inference job that summarizes city reviews.

Batch inference is for high-volume, cost-sensitive work that does NOT need an
instant answer. Instead of calling the model once per request (like
invoke_model / converse), you:

  1. Write a JSONL "manifest" - one line per request, each with a recordId and
     a modelInput (the same body shape you'd pass to invoke_model).
  2. Upload it to Amazon S3.
  3. Submit an async job. Bedrock runs every record and writes results back to
     an S3 output location.

Batch jobs are queued and can take a while (minutes to hours), and there is a
per-model minimum number of records (a service quota - check the Bedrock
console for the exact number; it is well over a hundred, so you cannot run a
tiny batch). This script generates 1000+ records to stay safely above it.

Usage:
    python summarize_batch.py                 # build + preview the JSONL manifest
    python summarize_batch.py --submit \\
        --bucket my-bucket --role-arn <arn>   # upload and start the batch job
    python summarize_batch.py --status <jobArn>   # check a running job
"""
import argparse
import json
import sys
import time

import boto3
from botocore.exceptions import ClientError

MODEL_ID = "amazon.nova-lite-v1:0"
REGION = "us-east-1"
MANIFEST_FILE = "batch_manifest.jsonl"

# A small base list of cities. We repeat it (with a suffix) to reach the record
# minimum - in real life these would be distinct records from your data.
BASE_CITIES = [
    "Albuquerque", "Denver", "Seattle", "Austin", "Miami", "Chicago",
    "Portland", "Nashville", "Boston", "Phoenix",
]

# How many records to generate. Batch has a per-model minimum (a quota); 1000
# keeps us comfortably above it.
RECORD_COUNT = 1000

SYSTEM_PROMPT = (
    "You are a travel expert AI assistant. Create comprehensive, engaging city "
    "summaries based on user reviews."
)


def build_record(record_id, city):
    """Build one manifest record in the format the batch job expects."""
    prompt = (
        f"Use the following reviews for {city} {{{{ REVIEWS EXCLUDED }}}}\n\n"
        f"Please provide a well-structured summary that includes:\n"
        f"1. Overall impression and sentiment\n2. Key highlights"
    )
    return {
        "recordId": record_id,
        "modelInput": {
            "schemaVersion": "messages-v1",
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "system": [{"text": SYSTEM_PROMPT}],
            "inferenceConfig": {
                "maxTokens": 500,
                "topP": 0.9,
                "topK": 20,
                "temperature": 0.7,
            },
        },
    }


def build_manifest(path=MANIFEST_FILE, count=RECORD_COUNT):
    """Write a JSONL manifest with `count` records and return the record count."""
    with open(path, "w") as f:
        for i in range(count):
            city = BASE_CITIES[i % len(BASE_CITIES)]
            # recordId must be unique per record
            record_id = f"{city.lower()}-{i:04d}"
            f.write(json.dumps(build_record(record_id, city)) + "\n")
    return count


def submit_job(bucket, role_arn, region=REGION, path=MANIFEST_FILE):
    """Upload the manifest to S3 and start a batch inference job.

    Requires:
      - an S3 bucket you can write to
      - an IAM service role whose trust policy allows bedrock.amazonaws.com to
        assume it, with S3 read/write on the input/output prefixes.
    """
    s3 = boto3.client("s3", region_name=region)
    bedrock = boto3.client("bedrock", region_name=region)

    input_key = f"batch-input/{path}"
    output_prefix = "batch-output/"

    print(f"Uploading {path} to s3://{bucket}/{input_key} ...")
    s3.upload_file(path, bucket, input_key)

    print("Submitting batch inference job ...")
    response = bedrock.create_model_invocation_job(
        jobName=f"summarize-reviews-{int(time.time())}",
        roleArn=role_arn,
        modelId=MODEL_ID,
        inputDataConfig={
            "s3InputDataConfig": {"s3Uri": f"s3://{bucket}/{input_key}"}
        },
        outputDataConfig={
            "s3OutputDataConfig": {"s3Uri": f"s3://{bucket}/{output_prefix}"}
        },
    )
    job_arn = response["jobArn"]
    print(f"Submitted. Job ARN:\n{job_arn}")
    print("\nBatch jobs run asynchronously - check back later with:")
    print(f"  python summarize_batch.py --status {job_arn}")
    return job_arn


def check_status(job_arn, region=REGION):
    """Print the status and progress of a batch inference job."""
    bedrock = boto3.client("bedrock", region_name=region)
    job = bedrock.get_model_invocation_job(jobIdentifier=job_arn)
    print("Status:", job["status"])
    if "message" in job:
        print("Message:", job["message"])
    print("Output location:", job["outputDataConfig"]["s3OutputDataConfig"]["s3Uri"])


def main():
    parser = argparse.ArgumentParser(description="Bedrock batch summarization demo.")
    parser.add_argument("--submit", action="store_true",
                        help="Upload the manifest to S3 and start the batch job.")
    parser.add_argument("--bucket", help="S3 bucket for input/output (with --submit).")
    parser.add_argument("--role-arn", help="Bedrock batch service role ARN (with --submit).")
    parser.add_argument("--status", metavar="JOB_ARN",
                        help="Check the status of a running batch job.")
    args = parser.parse_args()

    try:
        if args.status:
            check_status(args.status)
            return 0

        # Always build the manifest first
        count = build_manifest()
        print(f"Wrote {count} records to {MANIFEST_FILE}")
        with open(MANIFEST_FILE) as f:
            print("\nFirst record:")
            print(json.dumps(json.loads(f.readline()), indent=2))

        if args.submit:
            if not args.bucket or not args.role_arn:
                print("\n--submit requires --bucket and --role-arn", file=sys.stderr)
                return 1
            submit_job(args.bucket, args.role_arn)
        else:
            print("\nManifest ready. To actually run the batch job (async, needs "
                  "S3 + an IAM role):")
            print("  python summarize_batch.py --submit --bucket <bucket> "
                  "--role-arn <role-arn>")
        return 0
    except ClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
