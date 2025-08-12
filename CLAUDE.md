# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Local Development
- `python -m venv .venv && source .venv/bin/activate` - Setup virtual environment
- `python -m pip install -r requirements.txt` - Install dependencies
- `python -m uvicorn app:app --reload` - Run development server (localhost:8000)

### Docker
- `make build` - Build Docker image (`langextract-api:latest`)
- `make run` - Run container with proper environment (port 8080)

### Testing
- `make test-extract` - Test the `/extract` endpoint with sample config
- `make test-visualize` - Test the `/visualize` endpoint (requires API key)
- `curl http://localhost:8080/health` - Health check
- `curl http://localhost:8080/docs` - OpenAPI documentation

## Architecture Overview

This is a FastAPI-based HTTP wrapper around Google's LangExtract library for information extraction.

### Core Components

**app.py:88-96** - Health and version endpoints
**app.py:98-104** - `/extract` endpoint (returns JSON only)
**app.py:107-151** - `/visualize` endpoint (creates artifacts + HTML reports)
**app.py:154-165** - Artifact serving endpoint

### Key Data Flow

1. **Request Processing**: `ExtractRequest` DTOs are converted to LangExtract parameters via `_to_examples()` function
2. **Extraction**: Core logic in `_extract()` function calls `lx.extract()` with cleaned parameters
3. **Response Handling**: 
   - `/extract`: Returns JSON-encoded results via `jsonable_encoder`
   - `/visualize`: Uses raw results for proper LangExtract visualization
4. **Artifact Generation**: `/visualize` saves raw results via `lx_io.save_annotated_documents()`, then generates HTML via `lx.visualize()`

### Authentication Patterns

- **Per-request**: Use `X-API-Key` header or `provider_api_key` in request body
- **Server-held**: Set `LANGEXTRACT_API_KEY` environment variable (follows library standard)
- **Dependency**: `require_api_key()` function handles both patterns

### Environment Variables

- `MODEL_ID` - Default model (gemini-2.5-flash)
- `LANGEXTRACT_API_KEY` - Server-held provider key (standard library env var)
- `ARTIFACTS_DIR` - Where `/visualize` writes files (defaults to ./artifacts)
- `ALLOW_EMPTY_EXAMPLES` - Set to "true" to bypass examples validation (testing only)

### File Structure

- `models.py` - Pydantic DTOs for request/response schemas
- `app.py` - Main FastAPI application
- `examples/config.sample.json` - Sample request payload
- `artifacts/` - Generated extraction reports (timestamped directories)

### Important Implementation Notes

- Never pass None values to LangExtract - let library defaults apply
- Artifacts are constrained to `ARTIFACTS_DIR` to prevent path traversal
- JSONL output uses LangExtract's `save_annotated_documents()` with manual fallback
- HTML visualization generated via `lx.visualize()` function