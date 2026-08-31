# Show the actual HTTP request and response for a Bedrock call, formatted
# like the Headers tab in Chrome DevTools. Sensitive auth headers are redacted.
import json
import boto3

# Headers whose values are secrets - show that they exist but hide the value
SENSITIVE = {"authorization", "x-amz-security-token"}


def clean_headers(headers):
    """Decode header values to plain strings and redact secrets."""
    result = {}
    for key, value in headers.items():
        if isinstance(value, bytes):
            value = value.decode()
        if key.lower() in SENSITIVE:
            value = "<redacted>"
        result[key] = value
    return result


def show_request(request, **kwargs):
    print("=== REQUEST ===")
    print(request.method, request.url)
    print(json.dumps(clean_headers(request.headers), indent=2))


bedrock = boto3.client("bedrock", region_name="us-east-1")

# Fire the hook right before the request is sent over the wire
bedrock.meta.events.register("before-send.bedrock.ListFoundationModels", show_request)

response = bedrock.list_foundation_models()

print("\n=== RESPONSE ===")
meta = response["ResponseMetadata"]
print("HTTP status:", meta["HTTPStatusCode"])
print(json.dumps(meta["HTTPHeaders"], indent=2))
