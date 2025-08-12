import os
import uuid
import datetime
import pathlib
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder
import langextract as lx
import langextract.io as lx_io

from models import (
    ExampleDataDTO,
    ExtractRequest,
    ExtractResponse,
)

APP_NAME = "LangExtract API"
MODEL_DEFAULT = os.getenv("MODEL_ID", "gemini-2.5-flash")
API_KEY = os.getenv("LANGEXTRACT_API_KEY", "dev-key")
ARTIFACTS_DIR = pathlib.Path(os.getenv("ARTIFACTS_DIR", str(pathlib.Path.cwd() / "artifacts"))).resolve()
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="LangExtract API",
    version="1.0.0",
    description=(
        "HTTP wrapper around Google's LangExtract library.\n\n"
        "- `POST /extract` → JSON results\n"
        "- `POST /visualize` → also write JSONL + HTML to /artifacts\n"
        "- `GET  /health` → liveness\n"
        "- `GET  /version` → defaults\n"
    ),
)


def require_api_key(x_api_key: str | None = Header(None)):
    # Use header API key if provided, otherwise fall back to environment variable
    return x_api_key if x_api_key is not None else API_KEY


def _to_examples(objs: Optional[List[ExampleDataDTO]]):
    """Convert incoming DTOs into LangExtract ExampleData models."""
    if not objs:
        return None
    return [
        lx.data.ExampleData(
            text=o.text,
            extractions=[
                lx.data.Extraction(
                    extraction_class=e.extraction_class,
                    extraction_text=e.extraction_text,
                    attributes=e.attributes,
                )
                for e in o.extractions
            ],
        )
        for o in objs
    ]

def _extract(req: ExtractRequest, api_key: str | None, return_raw: bool = False):
    # Validate examples are provided (required by LangExtract for reliable results)
    allow_empty_examples = os.getenv("ALLOW_EMPTY_EXAMPLES", "false").lower() == "true"
    if not req.examples and not allow_empty_examples:
        raise ValueError("Examples are required for reliable extraction results. Set ALLOW_EMPTY_EXAMPLES=true to override for testing.")
    
    # Build kwargs and DO NOT pass None values (let LangExtract defaults apply)
    kwargs = {
        "text_or_documents": req.text_or_documents,
        "prompt_description": req.prompt_description,
        "examples": _to_examples(req.examples),
        "model_id": req.model_id or MODEL_DEFAULT,
    }
    if api_key is not None:
        kwargs["api_key"] = api_key
    if req.extraction_passes is not None:
        kwargs["extraction_passes"] = req.extraction_passes
    if req.max_workers is not None:
        kwargs["max_workers"] = req.max_workers
    if req.max_char_buffer is not None:
        kwargs["max_char_buffer"] = req.max_char_buffer
    if req.debug is not None:
        kwargs["debug"] = req.debug

    raw = lx.extract(**kwargs)

    # Return raw result for visualization or cleaned JSON for API responses
    if return_raw:
        return raw
    return jsonable_encoder(raw, exclude_none=False)


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.datetime.now(datetime.timezone.utc).isoformat()}


@app.get("/version")
def version():
    return {"app": APP_NAME, "model_default": MODEL_DEFAULT}


@app.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest, api_key: str = Depends(require_api_key)):
    try:
        data = _extract(req, api_key)
        return {"data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the full error for debugging while returning safe message
        import traceback
        print(f"LangExtract error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@app.post("/visualize")
def visualize(req: ExtractRequest, api_key: str = Depends(require_api_key)):
    """
    Run extraction and persist JSONL + an HTML report under ARTIFACTS_DIR.
    Returns file paths. Use GET /artifacts/html?path=... to fetch the HTML.
    """
    try:
        # Get raw results for visualization (not JSON-encoded)
        raw_results = _extract(req, api_key, return_raw=True)

        # Create run dir
        run_id = str(uuid.uuid4())[:8]
        base = ARTIFACTS_DIR / f"run_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{run_id}"
        base.mkdir(parents=True, exist_ok=True)

        # Save results using LangExtract's built-in save function
        # This handles the proper format for visualization
        jsonl_filename = "extraction_results.jsonl"
        lx_io.save_annotated_documents(
            raw_results if isinstance(raw_results, list) else [raw_results],
            output_name=jsonl_filename,
            output_dir=str(base)
        )
        
        jsonl_path = base / jsonl_filename

        # Generate interactive HTML visualization from the JSONL
        html_path = base / "report.html"
        html_text = lx.visualize(str(jsonl_path))
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_text)

        return {
            "run_dir": str(base),
            "jsonl": str(jsonl_path),
            "html": str(html_path),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the full error for debugging while returning safe message
        import traceback
        print(f"Visualization error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Visualization failed: {str(e)}")


@app.get("/artifacts/html")
def get_html(path: str = Query(..., description="Absolute path to report.html produced by /visualize")):
    """
    Serve a previously generated HTML report. For local/dev usage.
    """
    p = pathlib.Path(path).resolve()
    # Constrain to ARTIFACTS_DIR to avoid traversal
    if not str(p).startswith(str(ARTIFACTS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Path is outside artifacts directory")
    if not p.exists() or p.suffix.lower() != ".html":
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(p, media_type="text/html")
