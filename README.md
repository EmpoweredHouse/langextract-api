# LangExtract API (FastAPI wrapper)

A thin HTTP service around `google/langextract` that lets you use its information-extraction capabilities from any language over HTTP. It adds:

- A stable JSON API with OpenAPI docs
- Two auth modes (server-held key, or per-request key)
- Optional artifacts (JSONL + HTML) for audits/review
- Clean JSON serialization (Enums → strings, Pydantic → dicts)
- Docker/Compose for easy deployment

> If you’re evaluating whether this exists at all: `langextract` is a Python library. This wrapper makes it production-friendly to call from Elixir/Go/JS/etc.

---

## Why this project

- **Language-agnostic integration**: call LangExtract from anything via HTTP.
- **Team workflows**: persist JSONL and HTML reviews of extractions.
- **Configurable keys**: use one server-held provider key or accept per-request keys for multi-tenant scenarios.
- **Operational clarity**: observability-ready structure, clear envs and knobs, and clean failure modes.

---

## API surface

- `POST /extract` → returns extraction JSON only (no files written)
- `POST /visualize` → returns JSON and writes artifacts (JSONL + HTML report)
- `GET /artifacts/html?path=<abs_path>` → serves an HTML report produced by `/visualize` (dev/local use)
- `GET /health` → liveness
- `GET /version` → defaults

OpenAPI/Swagger is available at `/docs`. ReDoc is available at `/redoc`.

---

## Request schema (ExtractRequest)

```jsonc
{
  "text_or_documents": "string | string[]",       // required: raw text, or array of texts (multi-doc)
  "prompt_description": "string",                  // required: what to extract
  "examples": [                                    // required by langextract: few-shot examples
    {
      "text": "string",
      "extractions": [
        {
          "extraction_class": "string",
          "extraction_text": "string",
          "attributes": { "any": "json" }
        }
      ]
    }
  ],

  // Optional tuning
  "extraction_passes": 1,                          // integer; >1 increases recall & cost
  "max_workers": 4,                                // integer; parallelization
  "max_char_buffer": 1000,                         // integer; chunk size per call

  // Optional model override
  "model_id": "gemini-2.5-flash",

  // Optional: reduce verbose fields (debug defaults are controlled by the library)
  "debug": false,

  // Optional: if you prefer sending provider key in the body (alternatively use headers)
  "provider_api_key": "<KEY>"
}
````

**Response (ExtractResponse)**

* Single input → `{"data": { ...document... }}`
* Multiple inputs → `{"data": [ ...document..., ... ]}`

`document` is LangExtract’s `AnnotatedDocument` serialized to JSON. Expect fields like:

* `text` (original text)
* `extractions[]` with: `extraction_class`, `extraction_text`, `char_interval{start_pos,end_pos}`, `alignment_status`, `attributes`, etc.
* Some underscore fields may appear when `debug=true` (e.g., `_token_interval`).

---

## Auth patterns

You can run either way:

### A) **Per-request API key** (recommended for multi-tenant)

Send the provider API key in a header on each request. Supported headers:

* `X-API-Key` (preferred)
* `X-Gemini-Key` (alias)
  Or include `"provider_api_key"` in the JSON body.

### B) **Server-held API key** (single-tenant/internal)

Set `LANGEXTRACT_API_KEY` (and optionally `GEMINI_API_KEY`) as an environment variable for the container/process. Clients do not send keys.

---

## Environment variables

* `MODEL_ID` — default model id (e.g., `gemini-2.5-flash`)
* `ARTIFACTS_DIR` — where `/visualize` writes artifacts. Defaults to `./artifacts` when running locally.
* `LANGEXTRACT_API_KEY` — server-held provider key (optional if you use per-request)
* `GEMINI_API_KEY` — some providers/tools also read this var (optional)
* (Optional) `ALLOW_EMPTY_EXAMPLES` — if you set this to `true`, the API will allow requests without examples for smoke tests (not recommended in real use)

---

## Quickstart (local)

```bash
# Clone repo and cd in
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Run (server-held key)
export LANGEXTRACT_API_KEY="<YOUR_PROVIDER_KEY>"
export MODEL_ID="gemini-2.5-flash"
python -m uvicorn app:app --reload

# Or run without server-held key, and pass key per request instead
python -m uvicorn app:app --reload
```

Open docs:

```
http://127.0.0.1:8000/docs
```

---

## Quickstart (Docker)

```bash
docker build -t langextract-api:latest .
mkdir -p artifacts
```

**Per-request key (no secrets in container env):**

```bash
docker run --rm -p 8080:8080 \
  -e MODEL_ID=gemini-2.5-flash \
  -v "$PWD/artifacts:/artifacts" \
  langextract-api:latest
```

**Server-held key (container env):**

```bash
docker run --rm -p 8080:8080 \
  -e MODEL_ID=gemini-2.5-flash \
  -e LANGEXTRACT_API_KEY="<YOUR_PROVIDER_KEY>" \
  -e GEMINI_API_KEY="<YOUR_PROVIDER_KEY>" \
  -v "$PWD/artifacts:/artifacts" \
  langextract-api:latest
```

---

## Minimal tests

### Health

```bash
curl http://localhost:8080/health
```

### `/extract` (per-request key example)

```bash
curl -s -X POST http://localhost:8080/extract \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <YOUR_PROVIDER_KEY>' \
  -d '{
    "text_or_documents": "ROMEO: Juliet is the sun.",
    "prompt_description": "Extract characters (speakers).",
    "examples": [{
      "text": "HAMLET: To be, or not to be.",
      "extractions": [{
        "extraction_class": "character",
        "extraction_text": "HAMLET",
        "attributes": {"role": "speaker"}
      }]
    }],
    "extraction_passes": 1,
    "debug": false
  }' | jq .
```

### `/visualize` with sample config

Save as `examples/config.sample.json`:

```json
{
  "text_or_documents": [
    "ROMEO: Juliet is the sun.",
    "JULIET: O Romeo, Romeo!"
  ],
  "prompt_description": "Extract characters (speakers) from the dialogue.",
  "examples": [
    {
      "text": "HAMLET: To be, or not to be.",
      "extractions": [
        {
          "extraction_class": "character",
          "extraction_text": "HAMLET",
          "attributes": {"role": "speaker"}
        }
      ]
    }
  ],
  "extraction_passes": 2,
  "max_workers": 2,
  "debug": false
}
```

Run:

```bash
curl -s -X POST http://localhost:8080/visualize \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <YOUR_PROVIDER_KEY>' \
  -d @examples/config.sample.json | jq .
```

You’ll get:

```json
{
  "run_dir": ".../artifacts/run_YYYYMMDDThhmmssZ_xxxxxxxx",
  "jsonl": ".../extractions.jsonl",
  "html":  ".../report.html"
}
```

Open the HTML report (local filesystem):

```bash
open artifacts/<run_dir_basename>/report.html
```

Or via endpoint:

```bash
curl -o report.html \
  "http://localhost:8080/artifacts/html?path=$(jq -r .html <<< 'RESPONSE_JSON')"
open report.html
```

---

## Input shape tips

* **Examples are required** by LangExtract for reliable results. At least one minimal example is needed.
* `text_or_documents` can be a single string or an array of strings. Arrays return `data: [ ... ]` in the response.
* Use `extraction_passes > 1` only when you need higher recall; it reprocesses tokens and increases cost.
* `max_char_buffer` controls chunking; smaller values increase API calls.
* Set `debug: false` to suppress underscore debug fields in outputs and artifacts.

---

## Security

* Do not log API keys. The server does not log request bodies by default.
* Use TLS/HTTPS in front of this service in production.
* Add rate-limits upstream (e.g., gateway) to protect provider quotas and costs.
* For multi-tenant keys, prefer **per-request header** mode. Avoid global env shims.

---

## Troubleshooting

* **`ModuleNotFoundError: fastapi`**
  You ran outside the venv. Use `python -m venv .venv && source .venv/bin/activate && python -m pip install -r requirements.txt`, then `python -m uvicorn app:app --reload`.

* **Read-only `/artifacts`**
  On macOS/Linux, writing to root `/artifacts` may fail. This wrapper defaults to `./artifacts` locally. In Docker, mount `-v $PWD/artifacts:/artifacts`.

* **`ValueError: Examples are required...`**
  Provide at least one example in the request. That’s how LangExtract guides the model.

* **`'>' not supported between int and NoneType'`**
  You passed `null` in one of the numeric fields, overriding defaults. Omit optional fields entirely when not used.

* **Ugly `__objclass__` in JSON**
  That’s Enum internals leaking from naive serialization. This wrapper uses `jsonable_encoder` to output clean JSON (`alignment_status: "match_exact"` etc.).

* **Auth fails intermittently under concurrency**
  If you use global env vars for keys across multiple concurrent requests, you can get cross-talk. Prefer per-request `api_key` (header/body). If you must use env keys under concurrency, run separate instances per key.


## Versioning & compatibility

* We pin `langextract[all]` to `1.*` in `requirements.txt`. If you target a specific release or commit, pin it explicitly.
* The response envelope is deliberately loose (`data: dict | list[dict]`) to tolerate library model changes.

---

## License

* This wrapper: Apache-2.0
* LangExtract: Apache-2.0

---

## References / URLs

* GitHub: [https://github.com/google/langextract](https://github.com/google/langextract)
* Google Developers blog intro: [https://developers.googleblog.com/en/introducing-langextract-a-gemini-powered-information-extraction-library/](https://developers.googleblog.com/en/introducing-langextract-a-gemini-powered-information-extraction-library/)
* Health AI Developer Foundations page: [https://developers.google.com/health-ai-developer-foundations/libraries/langextract](https://developers.google.com/health-ai-developer-foundations/libraries/langextract)

```

If you want, I can also add a `docker-compose.yml`, GitHub Actions CI with a smoke test hitting `/health` and a mocked `/extract`, plus a `make demo` that boots the container and runs a sample request end-to-end.
