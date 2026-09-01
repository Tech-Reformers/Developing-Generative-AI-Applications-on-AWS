import boto3

# Instantiate a bedrock runtime client
bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")

MODEL_ID = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

# System instructions that steer the assistant for the whole conversation
system = [{"text": "You are a helpful assistant. Keep answers concise."}]

# The conversation history. Each turn (user and assistant) is appended here,
# so every request carries the full context and the model "remembers".
messages = []

print("Chat with Claude (streaming). Type 'exit' or 'quit' to stop.\n")

while True:
    user_input = input("You: ")
    if user_input.strip().lower() in ("exit", "quit"):
        print("Goodbye!")
        break

    # Add the user's message to the history
    messages.append({"role": "user", "content": [{"text": user_input}]})

    # Send the full history and stream the reply back
    response = bedrock_client.converse_stream(
        modelId=MODEL_ID,
        messages=messages,
        system=system,
        inferenceConfig={"temperature": 0.7, "maxTokens": 500},
    )

    # Print each chunk as it arrives, and build up the full reply text so we
    # can save it to the history afterward.
    print("\nClaude: ", end="", flush=True)
    reply = ""
    for event in response["stream"]:
        if "contentBlockDelta" in event:
            text = event["contentBlockDelta"]["delta"]["text"]
            print(text, end="", flush=True)
            reply += text
    print("\n")

    # Add the assistant's reply to the history so the next turn has context
    messages.append({"role": "assistant", "content": [{"text": reply}]})
