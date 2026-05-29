import json
import time
from pathlib import Path
from typing import List

from openai import OpenAI
from utils.vlm import get_client


def build_batch_request(
    custom_id: str,
    model_id: str,
    user_content: dict | List[dict] | List[List[dict]],
    max_tokens: int,
    temperature: float,
    seed: int,
) -> dict:
    """Build a single batch request line (dict) in the OpenAI Batch API format."""
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": model_id,
            "messages": [{"role": "user", "content": user_content}],
            "max_completion_tokens": max_tokens,
        },
    }


def _write_batch_file(requests: List[dict], output_path: Path) -> Path:
    """Write a list of batch request dicts to a .jsonl file.

    Returns the path to the written file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for req in requests:
            f.write(json.dumps(req) + "\n")
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(
        f"  Batch file written ({len(requests)} requests, {size_mb:.1f} MB): {output_path}"
    )
    return output_path


def _submit_batch(
    client: OpenAI,
    batch_file_path: Path,
    description: str = "",
) -> str:
    """Upload the .jsonl file and create a batch.

    Returns the batch id."""
    with open(batch_file_path, "rb") as f:
        uploaded = client.files.create(file=f, purpose="batch")

    batch = client.batches.create(
        input_file_id=uploaded.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={"description": description} if description else None,
    )
    print(f"  Batch created: {batch.id} (status: {batch.status})")
    return batch.id


def _poll_batch(
    client: OpenAI,
    batch_id: str,
    initial_delay: float = 10.0,
    max_delay: float = 300.0,
    backoff_factor: float = 1.5,
) -> str:
    """Poll until the batch reaches a terminal state.

    Returns the output_file_id on success, raises on failure/expiry.
    """
    delay = initial_delay
    terminal_states = {"completed", "failed", "expired", "cancelled"}

    while True:
        batch = client.batches.retrieve(batch_id)
        status = batch.status
        counts = batch.request_counts
        if status == "validating" or not counts:
            print(f"  Batch {batch_id}: {status} (checking input file...)")
        else:
            print(
                f"  Batch {batch_id}: {status} "
                f"({counts.completed}/{counts.total} done, {counts.failed} failed)"
            )

        if status in terminal_states:
            if status == "completed":
                return batch.output_file_id  # type: ignore
            if batch.error_file_id:
                error_content = client.files.content(batch.error_file_id).text
                raise RuntimeError(
                    f"Batch {batch_id} ended with status '{status}'.\n"
                    f"Error details:\n{error_content[:2000]}"
                )
            raise RuntimeError(f"Batch {batch_id} ended with status '{status}'.")

        time.sleep(delay)
        delay = min(delay * backoff_factor, max_delay)


def _download_and_parse_results(
    client: OpenAI,
    output_file_id: str,
) -> dict[str, str]:
    """Download the batch output file and parse it into {custom_id: response_text}.

    Requests that errored within the batch are included with an empty string
    as the value, and a warning is printed.
    """
    print(f"  Downloading results from file {output_file_id}...")
    raw = client.files.content(output_file_id).text
    results: dict[str, str] = {}

    for line in raw.strip().splitlines():
        entry = json.loads(line)
        cid = entry["custom_id"]
        error = entry.get("error")
        if error:
            print(f"  WARNING: request '{cid}' failed: {error}")
            results[cid] = ""
            continue

        body = entry["response"]["body"]
        text = body["choices"][0]["message"]["content"] or ""
        results[cid] = text

    print(f"  Parsed {len(results)} results.")
    return results


def run_batch(
    model_id: str,
    requests: List[dict],
    batch_file_path: Path,
    description: str = "",
    max_retries: int = 3,
) -> dict[str, str]:
    """Write the .jsonl, submit, poll, and return results.
    Automatically retries failed or empty requests using the synchronous API.

    Returns {custom_id: response_text}.
    """
    client = get_client(model_id)

    _write_batch_file(requests, batch_file_path)
    batch_id = _submit_batch(client, batch_file_path, description)
    output_file_id = _poll_batch(client, batch_id)
    results = _download_and_parse_results(client, output_file_id)

    # Retry failed requests synchronously up to max_retries times with exponential backoff
    failed_requests = [req for req in requests if not results.get(req["custom_id"])]
    if failed_requests:
        print(
            f"  Found {len(failed_requests)} failed requests. Retrying synchronously..."
        )
        for req in failed_requests:
            cid = req["custom_id"]
            body = req["body"]

            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model=body["model"],
                        messages=body["messages"],
                        max_completion_tokens=body.get("max_completion_tokens"),
                    )

                    content = response.choices[0].message.content
                    if content:
                        results[cid] = content
                        print(f"    [Success] Recovered {cid} on attempt {attempt + 1}")
                        break
                    else:
                        print(
                            f"    [Warning] {cid} returned empty content on attempt {attempt + 1}"
                        )

                except Exception as e:
                    print(f"    [Error] {cid} failed on attempt {attempt + 1}: {e}")
                    time.sleep(2**attempt)

    return results
