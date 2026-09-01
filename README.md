# Developing Generative AI Applications on AWS

Demo files for the *Developing Generative AI Applications on AWS* course. These
short Python scripts show how to call Amazon Bedrock using the AWS SDK (boto3).

The demos come in two forms that share the same setup:

- **`.py` scripts** — run from the command line, show the code as a real Python file
- **`.ipynb` notebooks** — run interactively cell by cell, with rich output

The setup below is done once and works for all of them.

## Requirements

- Python 3.9 or newer
- An AWS account with access to Amazon Bedrock
- AWS credentials configured on the machine (see [AWS credentials](#aws-credentials))

## Setup

The steps below create an isolated Python environment (a "virtual environment",
or *venv*) so the demo dependencies don't affect the rest of your system.

Run these commands once from the project folder.

### macOS / Linux

```bash
# 1. Create the virtual environment
python3 -m venv venv

# 2. Activate it (your prompt will show "(venv)")
source venv/bin/activate

# 3. Install the dependencies
pip install -r requirements.txt
```

### Windows

Using **PowerShell**:

```powershell
# 1. Create the virtual environment
python -m venv venv

# 2. Activate it (your prompt will show "(venv)")
venv\Scripts\Activate.ps1

# 3. Install the dependencies
pip install -r requirements.txt
```

Using **Command Prompt (cmd)**, the activation step is:

```cmd
venv\Scripts\activate.bat
```

> If PowerShell blocks the activation script, run PowerShell as Administrator
> once and execute:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

## AWS credentials

The demos need AWS credentials to call Bedrock. The easiest way is the AWS CLI:

```bash
aws configure
```

Enter your Access Key ID, Secret Access Key, and set the default region to
`us-east-1` (the region used in the demos).

> Make sure Amazon Bedrock model access is enabled for your account in the AWS
> Console (Bedrock > Model access).

## Running a demo

With the virtual environment activated, run any demo file by name:

The demos live in numbered topic folders (see [Demos](#demos) below). Run a
script from inside its folder:

```bash
cd 01_list_models
python list_models.py
```

## Running a notebook

Open any `.ipynb` file in VS Code / Kiro. When prompted, select the `venv` you
created above as the kernel (top-right of the notebook), then run cells with
Shift+Enter.

The first time, you may be asked to install the Jupyter extension. The
`jupyter` and `ipykernel` packages needed to run notebooks are already included
in `requirements.txt`.

## Deactivating the environment

When you're done, leave the virtual environment with:

```bash
deactivate
```

## Demos

Each topic lives in its own numbered folder, in teaching order. Each builds on
the one before it. Run demos from inside their folder.

### `01_list_models/`

| File | What it shows |
| --- | --- |
| `list_models.py` | The basic call: connect to Bedrock and list foundation models (name + ID). The `modelId` is what you pass when you invoke a model. |
| `list_models_pretty.py` | Same call, but prints the response as indented JSON so the structure is readable. |
| `list_models_logging.py` | Turns on botocore wire logging to show the raw HTTP request/response (the "firehose"). Note: real credentials appear in the logs. |
| `list_models_devtools.py` | A cleaner "under the hood" view — request method/URL/headers and response status, with secrets redacted. Like the DevTools Network tab. |
| `list_models.ipynb` | Notebook version: call → collapsible response tree → names + IDs → DevTools-style request/response. |

*Teaching/Learning Tip:* the `bedrock` client is the control plane (metadata about models); `bedrock-runtime` (below) is the data plane (actually running models).

### `02_invoke_model/`

| File | What it shows |
| --- | --- |
| `invoke_model.py` | Build a Claude-specific JSON payload (Anthropic Messages format), invoke the model, parse the response text. |
| `invoke_model_stream.py` | Same call with `invoke_model_with_response_stream` — reads the reply in chunks as it arrives (the "typing" effect). |
| `invoke_model.ipynb` | Notebook: build payload → invoke → read text → inspect the full response structure. |
| `invoke_model_stream.ipynb` | Notebook: stream the reply, then inspect the event chunks (`message_start`, `content_block_delta`, `message_stop`). |

*Teaching/Learning Tip:* `invoke_model` uses a different payload shape for every model family. Streaming is plain HTTPS (chunked), not WebSockets.

### `03_converse/`

| File | What it shows |
| --- | --- |
| `converse.py` | The modern, unified call: one `messages`/`system`/`inferenceConfig` structure that works across model families. |
| `converse_stream.py` | Same request, streamed via `converse_stream`. |
| `converse.ipynb` | Notebook: converse → response structure → converse_stream with its event types. |
| `converse_chat.py` | Interactive multi-turn chat in the terminal. Appends each turn to the history so the model remembers context. |
| `converse_chat_stream.py` | Interactive chat plus streaming replies — closest to a real chat app. |

*Teaching/Learning Tip:* Converse is AWS's recommended API. Swap the `modelId` and the same code calls Nova, Llama, etc. — no payload rewrite. The chat scripts show how conversation memory works: keep appending user and assistant messages to one `messages` list.

> **Note:** the Converse slides pass both `temperature` and `topP`. Claude Sonnet 4.5 rejects that combination, so the demos use `temperature` only (with `topP` commented out and explained).

### `04_synthetic_reviews/`

| File | What it shows |
| --- | --- |
| `generate_reviews.py` | Use Nova Lite to generate labeled city reviews (known sentiment + rating) and store them in DynamoDB. `--cleanup` deletes the table. |
| `generate_reviews.ipynb` | Notebook walkthrough with Teaching/Learning Tips, mapping to the four slides, plus a cleanup cell. |

*Teaching/Learning Tip:* an LLM can create labeled test data - control the sentiment before generating, so every review is pre-labeled. Uses Nova's own payload shape (`schemaVersion: "messages-v1"`), a nice contrast to Claude and to Converse.

### `05_batch/`

Summarize reviews at scale with an asynchronous batch job. See
`05_batch/README.md` for the full step-by-step flow.

| File | What it shows |
| --- | --- |
| `setup_batch.py` | Creates the S3 bucket and IAM role a batch job needs; `--cleanup` tears them down. |
| `summarize_batch.py` | Builds the JSONL manifest; `--submit` starts the job, `--status` checks it. |
| `summarize_batch.ipynb` | Notebook walkthrough of the manifest format and batch concepts. |

*Teaching/Learning Tip:* batch is the opposite tradeoff from streaming - it optimizes for cost and throughput on large volumes, not low latency. Jobs are async and have a per-model minimum record count, so batch is for bulk work, not one-off calls.
