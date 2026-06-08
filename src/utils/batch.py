import json
import time
from pathlib import Path
from typing import Callable, List

from google.genai import types
from google.genai.types import JOB_STATES_ENDED, JOB_STATES_SUCCEEDED
from openai import OpenAI
from utils.vlm import (
    _generate_response_gemini,
    content_to_gemini_parts_dict,
    gemini_generation_config_dict,
    get_client,
    get_gemini_client,
    parse_gemini_response_dict,
)


def build_batch_request(
    custom_id: str,
    model_id: str,
    user_content: dict | List[dict] | List[List[dict]],
    max_tokens: int,
    temperature: float,
    seed: int,
    use_gemini: bool = False,
) -> dict:
    """Build a single batch request line depending on the API being used (OpenAI or Gemini)."""
    if use_gemini:
        return {
            "custom_id": custom_id,
            "user_content": user_content,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "seed": seed,
        }
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


def _poll_gemini_batch(
    client,
    job_name: str,
    initial_delay: float = 10.0,
    max_delay: float = 300.0,
    backoff_factor: float = 1.5,
) -> str:
    """Poll until the Gemini batch job reaches a terminal state.

    Returns the output file resource name on success, raises otherwise.
    """
    delay = initial_delay
    while True:
        job = client.batches.get(name=job_name)
        state = getattr(job.state, "value", str(job.state))
        print(f"  Batch {job_name}: {state}")

        if state in JOB_STATES_ENDED:
            if state in JOB_STATES_SUCCEEDED:
                dest = job.dest
                if dest and dest.file_name:
                    return dest.file_name
                raise RuntimeError(
                    f"Batch {job_name} succeeded but produced no output file."
                )
            raise RuntimeError(
                f"Batch {job_name} ended with state '{state}': {job.error}"
            )

        time.sleep(delay)
        delay = min(delay * backoff_factor, max_delay)


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


def _download_and_parse_gemini_results(
    client,
    output_file_name: str,
    custom_ids: List[str],
) -> dict[str, str]:
    """Download the Gemini batch output file and parse it into {custom_id: text}."""
    print(f"  Downloading results from file {output_file_name}...")
    raw = client.files.download(file=output_file_name)
    text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw

    results: dict[str, str] = {}
    for idx, line in enumerate(text.strip().splitlines()):
        if not line:
            continue
        entry = json.loads(line)

        cid = entry.get("key")
        if cid is None:
            cid = custom_ids[idx] if idx < len(custom_ids) else f"_unknown_{idx}"

        if entry.get("error"):
            print(f"  WARNING: request '{cid}' failed: {entry['error']}")
            results[cid] = ""
            continue

        response = entry.get("response", entry)
        results[cid] = parse_gemini_response_dict(response)

    print(f"  Parsed {len(results)} results.")
    return results


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


def _retry_failed_requests(
    requests: List[dict],
    results: dict[str, str],
    execute: Callable[[dict], str | None],
    max_retries: int,
) -> None:
    """Retry requests with empty/missing results synchronously, updating ``results`` in place.

    ``execute`` runs a single request and returns its response text (or a falsy
    value if it produced nothing). Each failed request is attempted up to
    ``max_retries`` times, with exponential backoff after an exception.
    """
    failed_requests = [req for req in requests if not results.get(req["custom_id"])]
    if not failed_requests:
        return

    print(f"  Found {len(failed_requests)} failed requests. Retrying synchronously...")
    for req in failed_requests:
        cid = req["custom_id"]
        for attempt in range(max_retries):
            try:
                content = execute(req)
                if content:
                    results[cid] = content
                    print(f"    [Success] Recovered {cid} on attempt {attempt + 1}")
                    break
                print(
                    f"    [Warning] {cid} returned empty content on attempt {attempt + 1}"
                )
            except Exception as e:
                print(f"    [Error] {cid} failed on attempt {attempt + 1}: {e}")
                time.sleep(2**attempt)


def _build_gemini_batch_line(req: dict) -> dict:
    """Convert an internal Gemini request dict into a batch-input JSONL line."""
    return {
        "key": req["custom_id"],
        "request": {
            "contents": [
                {
                    "role": "user",
                    "parts": content_to_gemini_parts_dict(req["user_content"]),
                }
            ],
            "generationConfig": gemini_generation_config_dict(
                req["max_tokens"], req["temperature"], req["seed"]
            ),
        },
    }


def run_gemini_batch(
    model_id: str,
    requests: List[dict],
    batch_file_path: Path,
    description: str = "",
    max_retries: int = 3,
) -> dict[str, str]:
    """Write the .jsonl, upload it, submit the Gemini batch, poll, and return results.

    Failed or empty requests are retried synchronously. Returns {custom_id: text}.
    """
    client = get_gemini_client()

    _write_batch_file(
        [_build_gemini_batch_line(req) for req in requests], batch_file_path
    )

    uploaded = client.files.upload(
        file=str(batch_file_path),
        config=types.UploadFileConfig(
            display_name=description or batch_file_path.stem, mime_type="jsonl"
        ),
    )
    job = client.batches.create(
        model=model_id,
        src=uploaded.name,  # type: ignore
        config=(
            types.CreateBatchJobConfig(display_name=description)
            if description
            else None
        ),
    )
    print(
        f"  Batch created: {job.name} (state: {getattr(job.state, 'value', job.state)})"
    )

    output_file_name = _poll_gemini_batch(client, job.name)  # type: ignore
    custom_ids = [req["custom_id"] for req in requests]
    results = _download_and_parse_gemini_results(client, output_file_name, custom_ids)

    def _execute(req: dict) -> str | None:
        return _generate_response_gemini(
            model_id,
            req["user_content"],
            req["max_tokens"],
            req["temperature"],
            req["seed"],
        )

    _retry_failed_requests(requests, results, _execute, max_retries)
    return results


def run_batch(
    model_id: str,
    requests: List[dict],
    batch_file_path: Path,
    description: str = "",
    max_retries: int = 3,
    use_gemini: bool = False,
) -> dict[str, str]:
    """Write the .jsonl, submit, poll, and return results.
    Automatically retries failed or empty requests using the synchronous API.

    Returns {custom_id: response_text}.
    """
    if use_gemini:
        return run_gemini_batch(
            model_id, requests, batch_file_path, description, max_retries
        )

    client = get_client(model_id)

    _write_batch_file(requests, batch_file_path)
    batch_id = _submit_batch(client, batch_file_path, description)
    output_file_id = _poll_batch(client, batch_id)
    results = _download_and_parse_results(client, output_file_id)

    def _execute(req: dict) -> str | None:
        body = req["body"]
        response = client.chat.completions.create(
            model=body["model"],
            messages=body["messages"],
            max_completion_tokens=body.get("max_completion_tokens"),
        )
        return response.choices[0].message.content

    _retry_failed_requests(requests, results, _execute, max_retries)
    return results
