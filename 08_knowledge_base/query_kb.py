"""Query the Bedrock Knowledge Base with RetrieveAndGenerate.

This is the payoff of managed RAG. In one call, Bedrock:
  1. Embeds your question and searches the S3 Vectors index for relevant chunks
  2. Passes those chunks plus your question to a foundation model
  3. Returns a grounded answer *with citations* back to the source documents

Run setup_kb.py first - this reads the knowledge base id from kb_config.json.

Usage:
    python query_kb.py                    # ask the default demo question
    python query_kb.py "your question"    # ask your own
"""
import json
import sys

import boto3

DEFAULT_QUESTION = (
    "Which vendor has the largest market share, and what is the primary "
    "bottleneck for the industry?"
)


def main():
    question = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUESTION

    with open("kb_config.json") as f:
        kb_id = json.load(f)["knowledgeBaseId"]

    agent_runtime = boto3.client("bedrock-agent-runtime")
    region = agent_runtime.meta.region_name  # the resolved (CLI-configured) region
    account = boto3.client("sts").get_caller_identity()["Account"]

    # Model that writes the final answer from the retrieved chunks
    generation_model_arn = (
        f"arn:aws:bedrock:{region}:{account}:inference-profile/us.amazon.nova-lite-v1:0"
    )

    print(f"Question: {question}\n")
    response = agent_runtime.retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": generation_model_arn,
            },
        },
    )

    print("Answer:")
    print(response["output"]["text"])

    # Show where the answer came from
    citations = response.get("citations", [])
    refs = []
    for c in citations:
        for ref in c.get("retrievedReferences", []):
            loc = ref.get("location", {})
            uri = loc.get("s3Location", {}).get("uri", "?")
            refs.append(uri)
    if refs:
        print("\nSources:")
        for uri in sorted(set(refs)):
            print(f"  - {uri}")


if __name__ == "__main__":
    main()
