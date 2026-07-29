import hashlib
import json
import time
from pathlib import Path
from typing import Callable, List

from google.cloud import storage
from google.genai import types
from google.genai.types import JOB_STATES_ENDED, JOB_STATES_SUCCEEDED
from models import config
from openai import OpenAI
from utils.usage import record_completion_tokens
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
    """Poll until the Vertex batch job reaches a terminal state.

    Returns the GCS URI the results were written to on success, raises otherwise.
    """
    delay = initial_delay
    while True:
        job = client.batches.get(name=job_name)
        state = getattr(job.state, "value", str(job.state))
        print(f"  Batch {job_name}: {state}")

        if state in JOB_STATES_ENDED:
            if state in JOB_STATES_SUCCEEDED:
                dest = job.dest
                if dest and dest.gcs_uri:
                    return dest.gcs_uri
                raise RuntimeError(
                    f"Batch {job_name} succeeded but produced no output location."
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


NO_VERTEX_BATCH_MSG = (
    "Vertex AI batch prediction needs a GCP project and a GCS bucket to stage\n"
    "batch input and output:\n"
    "    GOOGLE_CLOUD_PROJECT=<project-id>\n"
    "    VERTEX_BATCH_BUCKET=gs://<bucket>[/<prefix>]\n"
    "    GOOGLE_CLOUD_LOCATION=<region>   (optional, defaults to 'global')\n"
    "plus application default credentials (gcloud auth application-default login).\n"
    "An express-mode API key cannot submit batch jobs; drop --batch to generate\n"
    "the responses synchronously instead."
)


def _split_gcs_uri(uri: str) -> tuple[str, str]:
    """Split "gs://bucket/some/prefix" into ("bucket", "some/prefix")."""
    bucket, _, blob = uri.removeprefix("gs://").strip("/").partition("/")
    return bucket, blob


def _gcs_bucket(bucket_name: str):
    return storage.Client(project=config.GOOGLE_CLOUD_PROJECT).bucket(bucket_name)


def _upload_batch_input(batch_file_path: Path) -> tuple[str, str]:
    """Copy the batch input file into the staging bucket.

    Vertex only reads batch input from GCS, so the local .jsonl is mirrored under
    VERTEX_BATCH_BUCKET at the same path as the run directory it belongs to.
    Returns the (input, output) GCS URIs.
    """
    base = config.VERTEX_BATCH_BUCKET.rstrip("/")  # type: ignore[union-attr]
    run_path = batch_file_path.parent.as_posix().strip("/")
    input_uri = f"{base}/{run_path}/{batch_file_path.name}"
    output_uri = f"{base}/{run_path}/batch_output/"

    bucket_name, blob_name = _split_gcs_uri(input_uri)
    _gcs_bucket(bucket_name).blob(blob_name).upload_from_filename(
        str(batch_file_path), content_type="application/jsonl"
    )
    print(f"  Batch input uploaded to {input_uri}")
    return input_uri, output_uri


def _download_vertex_results(output_uri: str) -> List[str]:
    """Return the lines of every .jsonl Vertex wrote under *output_uri*."""
    bucket_name, prefix = _split_gcs_uri(output_uri)
    blobs = [
        blob
        for blob in _gcs_bucket(bucket_name).list_blobs(prefix=prefix)
        if blob.name.endswith(".jsonl")
    ]
    if not blobs:
        raise RuntimeError(f"Batch produced no .jsonl output under {output_uri}.")

    lines: List[str] = []
    for blob in blobs:
        print(f"  Downloading results from gs://{bucket_name}/{blob.name}...")
        lines.extend(blob.download_as_text().strip().splitlines())
    return lines


def _request_fingerprint(request: dict) -> str:
    """Hash the prompt content of a batch request.

    Vertex rows carry no user-supplied id (unlike the Gemini Developer API's
    "key"), so responses are matched back to their custom_id through the request
    that every output row echoes.
    """
    parts: List[str] = []
    for content in request.get("contents") or []:
        for part in content.get("parts") or []:
            if part.get("text") is not None:
                parts.append("text:" + part["text"])
            else:
                inline = part.get("inlineData") or part.get("inline_data") or {}
                parts.append("image:" + str(inline.get("data", "")))
    return hashlib.sha256("\x00".join(parts).encode()).hexdigest()


def _parse_vertex_results(
    lines: List[str],
    custom_ids: List[str],
    fingerprints: List[str],
) -> dict[str, str]:
    """Parse Vertex batch output rows into {custom_id: text}."""
    pending: dict[str, List[str]] = {}
    for fingerprint, cid in zip(fingerprints, custom_ids):
        pending.setdefault(fingerprint, []).append(cid)

    results: dict[str, str] = {}
    for idx, line in enumerate(lines):
        if not line:
            continue
        entry = json.loads(line)

        matches = pending.get(_request_fingerprint(entry.get("request") or {}))
        if matches:
            cid = matches.pop(0)
        else:
            cid = custom_ids[idx] if idx < len(custom_ids) else f"_unknown_{idx}"
            print(f"  WARNING: output row {idx} matched no request, assuming '{cid}'.")

        if entry.get("status"):
            print(f"  WARNING: request '{cid}' failed: {entry['status']}")
            results[cid] = ""
            continue

        response = entry.get("response") or {}
        usage = response.get("usageMetadata") or {}
        record_completion_tokens(
            usage.get("candidatesTokenCount"), usage.get("thoughtsTokenCount")
        )
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
        record_completion_tokens((body.get("usage") or {}).get("completion_tokens"))
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
    """Convert an internal Gemini request dict into a batch-input JSONL line.

    Vertex accepts nothing but the request itself on a line, so the custom_id is
    not carried through; see _request_fingerprint for how results are matched.
    """
    return {
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
    """Stage the .jsonl in GCS, submit the Vertex batch, poll, and return results.

    Failed or empty requests are retried synchronously. Returns {custom_id: text}.
    """
    if not (config.GOOGLE_CLOUD_PROJECT and config.VERTEX_BATCH_BUCKET):
        raise RuntimeError(NO_VERTEX_BATCH_MSG)

    client = get_gemini_client()

    lines = [_build_gemini_batch_line(req) for req in requests]
    _write_batch_file(lines, batch_file_path)
    input_uri, output_uri = _upload_batch_input(batch_file_path)

    job = client.batches.create(
        model=model_id,
        src=input_uri,
        config=types.CreateBatchJobConfig(
            dest=output_uri,
            display_name=description or batch_file_path.stem,
        ),
    )
    print(
        f"  Batch created: {job.name} (state: {getattr(job.state, 'value', job.state)})"
    )

    dest_uri = _poll_gemini_batch(client, job.name)  # type: ignore
    results = _parse_vertex_results(
        _download_vertex_results(dest_uri),
        [req["custom_id"] for req in requests],
        [_request_fingerprint(line["request"]) for line in lines],
    )

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
        if response.usage:
            record_completion_tokens(response.usage.completion_tokens)
        return response.choices[0].message.content

    _retry_failed_requests(requests, results, _execute, max_retries)
    return results
