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

```bash
python <filename>.py
```

For example:

```bash
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
