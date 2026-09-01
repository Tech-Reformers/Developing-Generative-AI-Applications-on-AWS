# Same as list_models.py, but with wire-level logging turned on so you can
# see the actual HTTP request and response between your machine and Bedrock.
import boto3

# Turn on botocore logging (shows the request URL, headers, and raw response)
boto3.set_stream_logger("botocore")

# Instantiate a bedrock client
bedrock = boto3.client("bedrock", region_name="us-east-1")
# List foundation models
response = bedrock.list_foundation_models()

# Print each model's name and ID, one per line
for model in response["modelSummaries"]:
    print(model["modelName"], "-", model["modelId"])
