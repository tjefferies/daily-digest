"""Layer 5: Digest Generation - LLM-powered digest prose generation.

Converts ranked, scored atoms into natural-language digest prose
organized into four priority-tiered sections per persona.
"""

from evercurrent.generation.assembler import DigestAssembler
from evercurrent.generation.prompt import build_generation_prompt
from evercurrent.generation.runner import DigestGenerator

__all__ = [
    "DigestAssembler",
    "DigestGenerator",
    "build_generation_prompt",
]
