"""Stand up (or tear down) a Bedrock Knowledge Base backed by Amazon S3 Vectors.

This is managed RAG: point Bedrock at documents in S3, and it chunks them,
generates embeddings, and stores them in a vector index. You then query the
knowledge base and it retrieves the relevant chunks to ground the answer.

We use **S3 Vectors** as the vector store instead of OpenSearch Serverless.
S3 Vectors scales to zero and bills per storage/query, so a demo costs cents
rather than the ~$350/month an idle OpenSearch Serverless collection would.

NOTE: The S3 Vectors + Knowledge Bases integration is a preview feature and may
change. See the AWS docs for current details.

The pieces this creates, in order:
  1. S3 Vectors vector bucket + index (the vector store)
  2. S3 bucket for source documents + upload the sample PDF
  3. IAM service role Bedrock assumes (embed model + S3 read + s3vectors access)
  4. Knowledge base (S3_VECTORS storage)
  5. Data source (S3 connector, fixed-size chunking)
  6. Ingestion job (chunk + embed + store)

IDs are written to kb_config.json for query_kb.py to use.

Usage:
    python setup_kb.py            # create everything and start ingestion
    python setup_kb.py --cleanup  # delete everything
"""
import argparse
import json
import sys
import time

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
EMBED_MODEL = "amazon.titan-embed-text-v2:0"
EMBED_DIM = 1024

VECTOR_BUCKET = "bedrock-kb-vectors-demo"
INDEX_NAME = "kb-index"
DATA_BUCKET_PREFIX = "bedrock-kb-docs-demo"
ROLE_NAME = "BedrockKBDemoRole"
KB_NAME = "DemoKnowledgeBase"
SAMPLE_DOC = "sample_report.pdf"
CONFIG_FILE = "kb_config.json"

sts = boto3.client("sts", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)
s3vectors = boto3.client("s3vectors", region_name=REGION)
iam = boto3.client("iam")
bedrock_agent = boto3.client("bedrock-agent", region_name=REGION)


def account_id():
    return sts.get_caller_identity()["Account"]


def data_bucket():
    return f"{DATA_BUCKET_PREFIX}-{account_id()}"


# ---------- create ----------

def create_vector_store():
    try:
        s3vectors.create_vector_bucket(vectorBucketName=VECTOR_BUCKET)
        print(f"Created vector bucket: {VECTOR_BUCKET}")
    except ClientError as e:
        if "Conflict" in str(e) or "already" in str(e).lower():
            print(f"Vector bucket already exists: {VECTOR_BUCKET}")
        else:
            raise
    try:
        s3vectors.create_index(
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
            dataType="float32",
            dimension=EMBED_DIM,
            distanceMetric="cosine",
        )
        print(f"Created vector index: {INDEX_NAME}")
    except ClientError as e:
        if "Conflict" in str(e) or "already" in str(e).lower():
            print(f"Vector index already exists: {INDEX_NAME}")
        else:
            raise

    acct = account_id()
    bucket_arn = f"arn:aws:s3vectors:{REGION}:{acct}:bucket/{VECTOR_BUCKET}"
    index_arn = f"{bucket_arn}/index/{INDEX_NAME}"
    return bucket_arn, index_arn


def create_data_bucket():
    bucket = data_bucket()
    try:
        s3.create_bucket(Bucket=bucket)
        print(f"Created data bucket: {bucket}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"Data bucket already exists: {bucket}")
    s3.upload_file(SAMPLE_DOC, bucket, SAMPLE_DOC)
    print(f"Uploaded {SAMPLE_DOC} to s3://{bucket}/{SAMPLE_DOC}")
    return f"arn:aws:s3:::{bucket}"


def create_role(data_bucket_arn, vector_bucket_arn, index_arn):
    acct = account_id()
    trust = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {"StringEquals": {"aws:SourceAccount": acct}},
        }],
    }
    perms = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "InvokeEmbeddingModel",
                "Effect": "Allow",
                "Action": ["bedrock:InvokeModel"],
                "Resource": f"arn:aws:bedrock:{REGION}::foundation-model/{EMBED_MODEL}",
            },
            {
                "Sid": "ReadSourceDocuments",
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:ListBucket"],
                "Resource": [data_bucket_arn, f"{data_bucket_arn}/*"],
            },
            {
                "Sid": "AccessVectorStore",
                "Effect": "Allow",
                "Action": ["s3vectors:*"],
                "Resource": [vector_bucket_arn, index_arn],
            },
        ],
    }
    try:
        role = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust),
            Description="Service role for the Bedrock KB (S3 Vectors) demo.",
        )
        role_arn = role["Role"]["Arn"]
        print(f"Created role: {ROLE_NAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = iam.get_role(RoleName=ROLE_NAME)["Role"]["Arn"]
        print(f"Role already exists: {ROLE_NAME}")
    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName="BedrockKBDemoAccess",
        PolicyDocument=json.dumps(perms),
    )
    print("Attached KB access policy")
    return role_arn


def create_knowledge_base(role_arn, vector_bucket_arn, index_arn):
    acct = account_id()
    resp = bedrock_agent.create_knowledge_base(
        name=KB_NAME,
        roleArn=role_arn,
        knowledgeBaseConfiguration={
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": f"arn:aws:bedrock:{REGION}::foundation-model/{EMBED_MODEL}",
                "embeddingModelConfiguration": {
                    "bedrockEmbeddingModelConfiguration": {
                        "dimensions": EMBED_DIM,
                        "embeddingDataType": "FLOAT32",
                    }
                },
            },
        },
        storageConfiguration={
            "type": "S3_VECTORS",
            "s3VectorsConfiguration": {
                "vectorBucketArn": vector_bucket_arn,
                "indexArn": index_arn,
            },
        },
    )
    kb_id = resp["knowledgeBase"]["knowledgeBaseId"]
    print(f"Created knowledge base: {kb_id}")
    return kb_id


def create_data_source(kb_id, data_bucket_arn):
    resp = bedrock_agent.create_data_source(
        knowledgeBaseId=kb_id,
        name="S3-connector",
        description="S3 data source connector for Amazon Bedrock to use content in S3",
        dataSourceConfiguration={
            "type": "S3",
            "s3Configuration": {
                "bucketArn": data_bucket_arn,
                # inclusionPrefixes are literal S3 key prefixes, NOT regex.
                # We omit it so the whole bucket is ingested. (The slide's
                # ".*\\.pdf" is regex-style and would match nothing here.)
            },
        },
        vectorIngestionConfiguration={
            "chunkingConfiguration": {
                "chunkingStrategy": "FIXED_SIZE",
                "fixedSizeChunkingConfiguration": {
                    "maxTokens": 100,
                    "overlapPercentage": 10,
                },
            }
        },
    )
    ds_id = resp["dataSource"]["dataSourceId"]
    print(f"Created data source: {ds_id}")
    return ds_id


def start_ingestion(kb_id, ds_id):
    resp = bedrock_agent.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id)
    job_id = resp["ingestionJob"]["ingestionJobId"]
    print(f"Started ingestion job: {job_id}")
    # Poll until complete
    while True:
        job = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id, dataSourceId=ds_id, ingestionJobId=job_id
        )["ingestionJob"]
        status = job["status"]
        print(f"  ingestion status: {status}")
        if status in ("COMPLETE", "FAILED"):
            if status == "FAILED":
                print("  failure reasons:", job.get("failureReasons"))
            break
        time.sleep(10)
    return job_id


def create():
    vector_bucket_arn, index_arn = create_vector_store()
    data_bucket_arn = create_data_bucket()
    role_arn = create_role(data_bucket_arn, vector_bucket_arn, index_arn)

    # IAM propagation can lag; give it a moment before the KB assumes the role
    print("Waiting for IAM role to propagate ...")
    time.sleep(15)

    kb_id = create_knowledge_base(role_arn, vector_bucket_arn, index_arn)
    ds_id = create_data_source(kb_id, data_bucket_arn)
    start_ingestion(kb_id, ds_id)

    with open(CONFIG_FILE, "w") as f:
        json.dump({"knowledgeBaseId": kb_id, "dataSourceId": ds_id}, f, indent=2)
    print(f"\nSaved KB config to {CONFIG_FILE}. Query it with:")
    print("  python query_kb.py")


# ---------- cleanup ----------

def cleanup():
    acct = account_id()
    # Load IDs if we have them
    kb_id = ds_id = None
    try:
        cfg = json.load(open(CONFIG_FILE))
        kb_id, ds_id = cfg.get("knowledgeBaseId"), cfg.get("dataSourceId")
    except FileNotFoundError:
        pass

    # 1. Data source, then KB
    if kb_id and ds_id:
        try:
            bedrock_agent.delete_data_source(knowledgeBaseId=kb_id, dataSourceId=ds_id)
            print(f"Deleted data source: {ds_id}")
        except ClientError as e:
            print(f"data source delete: {e}")
    if kb_id:
        try:
            bedrock_agent.delete_knowledge_base(knowledgeBaseId=kb_id)
            print(f"Deleted knowledge base: {kb_id}")
        except ClientError as e:
            print(f"kb delete: {e}")

    # 2. IAM role
    try:
        iam.delete_role_policy(RoleName=ROLE_NAME, PolicyName="BedrockKBDemoAccess")
    except iam.exceptions.NoSuchEntityException:
        pass
    try:
        iam.delete_role(RoleName=ROLE_NAME)
        print(f"Deleted role: {ROLE_NAME}")
    except iam.exceptions.NoSuchEntityException:
        print(f"Role not found: {ROLE_NAME}")

    # 3. Data bucket
    bucket = data_bucket()
    try:
        res = boto3.resource("s3", region_name=REGION).Bucket(bucket)
        res.objects.all().delete()
        res.delete()
        print(f"Deleted data bucket: {bucket}")
    except ClientError as e:
        print(f"data bucket delete: {e}")

    # 4. Vector index, then vector bucket
    try:
        s3vectors.delete_index(vectorBucketName=VECTOR_BUCKET, indexName=INDEX_NAME)
        print(f"Deleted vector index: {INDEX_NAME}")
    except ClientError as e:
        print(f"index delete: {e}")
    try:
        s3vectors.delete_vector_bucket(vectorBucketName=VECTOR_BUCKET)
        print(f"Deleted vector bucket: {VECTOR_BUCKET}")
    except ClientError as e:
        print(f"vector bucket delete: {e}")

    try:
        import os
        os.remove(CONFIG_FILE)
    except FileNotFoundError:
        pass


def main():
    parser = argparse.ArgumentParser(description="Set up or tear down a Bedrock KB (S3 Vectors).")
    parser.add_argument("--cleanup", action="store_true", help="Delete all resources.")
    args = parser.parse_args()
    try:
        cleanup() if args.cleanup else create()
        return 0
    except ClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
