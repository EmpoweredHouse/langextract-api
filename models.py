from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ExtractionDTO(BaseModel):
    """
    Single extracted span/object.
    Mirrors langextract.data.Extraction fields we care about.
    """
    extraction_class: str
    extraction_text: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class ExampleDataDTO(BaseModel):
    """
    One training/example item for few-shot extraction.
    """
    text: str
    extractions: List[ExtractionDTO] = Field(default_factory=list)


class ExtractRequest(BaseModel):
    """
    Request body for /extract and /visualize.
    """
    model_config = ConfigDict(protected_namespaces=())
    
    text_or_documents: Union[str, List[str]]
    prompt_description: str
    examples: List[ExampleDataDTO] = Field(default_factory=list)

    # Tuning / performance knobs (all optional)
    extraction_passes: Optional[int] = None
    max_workers: Optional[int] = None
    max_char_buffer: Optional[int] = None

    # Model override (defaults to env MODEL_ID)
    model_id: Optional[str] = None

    # Toggle verbose debug fields coming from LangExtract (default is True in the lib).
    # If None, we don't pass it and let the library default apply.
    debug: Optional[bool] = True

class ExtractResponse(BaseModel):
    """
    Response envelope for /extract.
    - Single input (str/URL) → dict payload
    - Multiple docs (list)   → list[dict]
    """
    data: Union[Dict[str, Any], List[Dict[str, Any]]]