"""Layer 5: Digest Generation - LLM-powered digest prose generation.

Converts ranked, scored atoms into natural-language digest prose
organized into four priority-tiered sections per persona.
"""

from digest.generation.assembler import AsyncDigestAssembler
from digest.generation.prompt import build_generation_prompt
from digest.generation.runner import AsyncDigestGenerator

__all__ = [
    "AsyncDigestAssembler",
    "AsyncDigestGenerator",
    "build_generation_prompt",
]
