# Same Bedrock call, but we pretty-print the response as indented JSON
# so it's easy to read (like the JSON view in Chrome DevTools).
import json
import boto3

bedrock = boto3.client("bedrock", region_name="us-east-1")
response = bedrock.list_foundation_models()

# Show just the list of models, formatted with indentation
print(json.dumps(response["modelSummaries"], indent=2, default=str))
