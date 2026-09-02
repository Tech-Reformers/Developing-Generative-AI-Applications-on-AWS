# Batch Inference Demo

Summarize a large set of city reviews with Amazon Bedrock **batch inference**.

Unlike `invoke_model` or `converse` (one request, instant answer), batch
inference runs a model over many inputs at once, asynchronously. You write a
JSONL manifest, upload it to S3, submit a job, and pick up the results later.

## Files

| File | What it does |
| --- | --- |
| `setup_batch.py` | Creates the S3 bucket and IAM role the job needs (and tears them down with `--cleanup`). |
| `summarize_batch.py` | Builds the JSONL manifest; `--submit` uploads it and starts the job; `--status` checks a job. |
| `summarize_batch.ipynb` | Notebook walkthrough with Teaching/Learning Tips explaining the manifest and batch concepts. |
| `batch_manifest.json.out` | A real, completed job's output (1000 review summaries). Committed so you can show batch results **without** running a job. |

> **Teaching/Learning Tip:** batch jobs take minutes to hours, so they don't
> fit in a live lecture. Open `batch_manifest.json.out` to show finished
> results directly - each line pairs the request (`modelInput`) with the
> generated summary (`modelOutput`) and token usage.

## Why batch (Teaching/Learning Tip)

Batch is the opposite tradeoff from streaming. Streaming optimizes for *low
latency* - one answer, right now. Batch optimizes for *cost and throughput* on
large volumes, and in exchange it's not instant (jobs queue and can take minutes
to hours). There's also a per-model **minimum record count** (a service quota),
so batch is deliberately not for one-off calls - it's for bulk work.

## Prerequisites

- The virtual environment and AWS credentials from the top-level README
- Amazon Bedrock model access enabled for `amazon.nova-lite-v1:0`
- Permission to create an S3 bucket and an IAM role (the setup script does this)

## Running the demo

Run these from inside the `batch/` folder with the venv activated.

### 1. Preview the manifest (no AWS resources needed)

```bash
python summarize_batch.py
```

Writes `batch_manifest.jsonl` (1000 records) and prints the first one. Good for
showing the manifest format without submitting anything.

### 2. Create the AWS resources

```bash
python setup_batch.py
```

Creates an S3 bucket and an IAM service role, then prints the `--bucket` and
`--role-arn` values to use next.

> The IAM role's trust policy is scoped to your account (confused-deputy
> protection), and its S3 permissions are scoped to just this bucket.

### 3. Submit the batch job

```bash
python summarize_batch.py --submit \
    --bucket <bucket-from-step-2> \
    --role-arn <role-arn-from-step-2>
```

This uploads the manifest and starts the job, printing a **job ARN**. The job
runs asynchronously - it will not finish right away.

> **Teaching/Learning Tip:** Because batch is async, this is a great overnight
> or between-sessions activity. Submit it, move on, and check the results later.

### 4. Check the job status

```bash
python summarize_batch.py --status <job-arn>
```

When the status is `Completed`, the results are in the bucket under
`batch-output/`. Each input record's summary is matched back by its `recordId`.

### 5. Clean up (do this AFTER retrieving results)

```bash
python setup_batch.py --cleanup
```

Empties and deletes the bucket and deletes the IAM role.

> **Important:** Don't clean up while a job is still running - the job needs the
> input file in S3 and the role to write output. Wait until the job is
> `Completed` (or `Failed`) and you've downloaded what you need.

## Notes

- `batch_manifest.jsonl` is a generated file and is git-ignored.
- The demo repeats a base city list to reach 1000 records so it clears the
  per-model minimum. In a real pipeline, each record would be a distinct input
  (e.g. one city with its actual reviews).
