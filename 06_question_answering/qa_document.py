"""Question answering over a local document with the Converse API.

Instead of pasting a document's text into the prompt, Converse lets you attach
the file directly as a "document" content block. Bedrock parses it and the model
answers questions grounded in its contents. Supported formats include pdf, csv,
doc(x), xls(x), html, txt, and md.
"""
import json
import boto3

# Read the document as raw bytes
with open("sample_report.pdf", "rb") as file:
    doc_bytes = file.read()

# Build the message: a document block followed by the question about it
messages = [{
    "role": "user",
    "content": [
        {
            "document": {
                "format": "pdf",
                "name": "QuantumReport",
                "source": {"bytes": doc_bytes},
            }
        },
        {
            "text": "How many qubits of growth is projected by 2026, and how "
                    "does the actual trajectory differ?"
        },
    ],
}]

inf_params = {"maxTokens": 300, "topP": 0.1, "temperature": 0.3}
client = boto3.client("bedrock-runtime", region_name="us-east-1")
model_id = "us.amazon.nova-lite-v1:0"

model_response = client.converse(
    modelId=model_id,
    messages=messages,
    inferenceConfig=inf_params,
)

print("\n[Full Response]")
print(json.dumps(model_response, indent=2))
print("\n[Response Content Text]")
print(model_response["output"]["message"]["content"][0]["text"])
