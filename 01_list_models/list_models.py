# import AWS SDK for Python
import boto3
# Instantiate a bedrock client
bedrock = boto3.client("bedrock", region_name="us-east-1")
# List foundation models
response = bedrock.list_foundation_models()

# Print each model's name and ID, one per line
for model in response["modelSummaries"]:
    print(model["modelName"], "-", model["modelId"])
