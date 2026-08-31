import boto3

# Instantiate a bedrock runtime client
bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# System instructions that steer the assistant for the whole conversation
system = [{"text": "You are a helpful assistant. Keep answers concise."}]

# The conversation history. Each turn (user and assistant) is appended here,
# so every request carries the full context and the model "remembers".
messages = []

print("Chat with Claude. Type 'exit' or 'quit' to stop.\n")

while True:
    user_input = input("You: ")
    if user_input.strip().lower() in ("exit", "quit"):
        print("Goodbye!")
        break

    # Add the user's message to the history
    messages.append({"role": "user", "content": [{"text": user_input}]})

    # Send the full history to the model
    response = bedrock_client.converse(
        modelId=MODEL_ID,
        messages=messages,
        system=system,
        inferenceConfig={"temperature": 0.7, "maxTokens": 500},
    )

    # Extract the reply and show it
    reply = response["output"]["message"]["content"][0]["text"]
    print(f"\nClaude: {reply}\n")

    # Add the assistant's reply to the history so the next turn has context
    messages.append(response["output"]["message"])
