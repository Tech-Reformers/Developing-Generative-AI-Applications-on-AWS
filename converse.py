import boto3

# Instantiate a bedrock runtime client
bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")

# Send the message
response = bedrock_client.converse(
    modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
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

# Extract and print the response text
print(response["output"]["message"]["content"][0]["text"])
