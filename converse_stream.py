import boto3, sys

# Instantiate a bedrock runtime client
bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")

# Send the message (same request content as converse.py)
response = bedrock_client.converse_stream(
    modelId="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    messages=[{
        "role": "user",
        "content": [{"text": "Create a script to resize images."}]
    }],
    system=[{"text": "You are an app developer proficient in Python. Only "
                     "engage in discussion of coding topics."}],
    # Note: the slide also passes "topP": 0.9, but Claude Sonnet 4.5 rejects
    # temperature and topP together ("cannot both be specified"). Use one or
    # the other. Uncomment topP below (and remove temperature) to try it.
    inferenceConfig={"temperature": 0.7, "maxTokens": 500},  # "topP": 0.9,
    additionalModelRequestFields={"top_k": 200}
)

# Read chunks from the stream and print only content chunks in real time
for event in response["stream"]:
    if "contentBlockDelta" in event:
        chunk = event["contentBlockDelta"]
        sys.stdout.write(chunk["delta"]["text"])
        sys.stdout.flush()
