"""Layer 2: Extraction Pipeline - LLM-powered atom extraction.

Transforms ingested context windows into structured Atom objects
using the Anthropic Claude API via batch processing.
"""

from evercurrent.extraction.batch_runner import BatchExtractionRunner
from evercurrent.extraction.filter import FilterResult, confidence_filter
from evercurrent.extraction.prompt import build_coarse_prompt, build_enrichment_prompt
from evercurrent.extraction.validation import async_validate_atoms

__all__ = [
    "BatchExtractionRunner",
    "FilterResult",
    "async_validate_atoms",
    "build_coarse_prompt",
    "build_enrichment_prompt",
    "confidence_filter",
]
