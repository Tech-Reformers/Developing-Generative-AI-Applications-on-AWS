"""Create (or tear down) the AWS resources a Bedrock batch inference job needs:

  - An S3 bucket for the input manifest and the output results.
  - An IAM service role that Bedrock assumes to read the input and write the
    output, with a trust policy scoped to this account (confused-deputy
    protection) and S3 permissions scoped to the bucket.

Usage:
    python setup_batch.py            # create the bucket and role, print their names
    python setup_batch.py --cleanup  # delete the role and empty/delete the bucket

The names are derived from your account ID so they're stable across runs.
"""
import argparse
import json
import sys

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
ROLE_NAME = "BedrockBatchDemoRole"
POLICY_NAME = "BedrockBatchDemoS3Access"


def account_id():
    return boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]


def bucket_name():
    # Bucket names are globally unique; scope to the account to avoid clashes.
    return f"bedrock-batch-demo-{account_id()}"


def trust_policy(acct):
    """Allow Bedrock to assume the role, scoped to this account (confused-deputy safe)."""
    return {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {"aws:SourceAccount": acct},
                "ArnLike": {
                    "aws:SourceArn": f"arn:aws:bedrock:{REGION}:{acct}:model-invocation-job/*"
                },
            },
        }],
    }


def s3_policy(bucket):
    """Least-privilege S3 access scoped to the demo bucket."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject"],
                "Resource": f"arn:aws:s3:::{bucket}/*",
            },
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": f"arn:aws:s3:::{bucket}",
            },
        ],
    }


def create():
    acct = account_id()
    bucket = bucket_name()
    s3 = boto3.client("s3", region_name=REGION)
    iam = boto3.client("iam")

    # 1. S3 bucket (us-east-1 does not take a LocationConstraint)
    try:
        s3.create_bucket(Bucket=bucket)
        print(f"Created bucket: {bucket}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"Bucket already exists: {bucket}")

    # 2. IAM role with the Bedrock trust policy
    try:
        role = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy(acct)),
            Description="Service role for Bedrock batch inference demo.",
        )
        role_arn = role["Role"]["Arn"]
        print(f"Created role: {ROLE_NAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = iam.get_role(RoleName=ROLE_NAME)["Role"]["Arn"]
        print(f"Role already exists: {ROLE_NAME}")

    # 3. Inline S3 access policy scoped to the bucket
    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName=POLICY_NAME,
        PolicyDocument=json.dumps(s3_policy(bucket)),
    )
    print(f"Attached S3 policy: {POLICY_NAME}")

    print("\nSetup complete. Use these with the batch job:")
    print(f"  --bucket {bucket}")
    print(f"  --role-arn {role_arn}")
    print("\nExample:")
    print(f"  python summarize_batch.py --submit --bucket {bucket} --role-arn {role_arn}")


def cleanup():
    bucket = bucket_name()
    s3 = boto3.resource("s3", region_name=REGION)
    iam = boto3.client("iam")

    # 1. Empty and delete the bucket
    try:
        b = s3.Bucket(bucket)
        b.objects.all().delete()
        b.delete()
        print(f"Deleted bucket: {bucket}")
    except s3.meta.client.exceptions.NoSuchBucket:
        print(f"Bucket not found (already gone): {bucket}")

    # 2. Remove the inline policy, then delete the role
    try:
        iam.delete_role_policy(RoleName=ROLE_NAME, PolicyName=POLICY_NAME)
    except iam.exceptions.NoSuchEntityException:
        pass
    try:
        iam.delete_role(RoleName=ROLE_NAME)
        print(f"Deleted role: {ROLE_NAME}")
    except iam.exceptions.NoSuchEntityException:
        print(f"Role not found (already gone): {ROLE_NAME}")


def main():
    parser = argparse.ArgumentParser(description="Set up or tear down Bedrock batch resources.")
    parser.add_argument("--cleanup", action="store_true",
                        help="Delete the bucket and role instead of creating them.")
    args = parser.parse_args()

    try:
        if args.cleanup:
            cleanup()
        else:
            create()
        return 0
    except ClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
