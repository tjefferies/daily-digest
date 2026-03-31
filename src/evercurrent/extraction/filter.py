"""Confidence threshold filter for extracted atoms.

Filters atoms by confidence score, placing those below the threshold
into a low-confidence bucket. Default threshold is 0.7 per section 4.4.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from evercurrent.models.atom import Atom

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 0.7


@dataclass
class FilterResult:
    """Result of confidence filtering.

    Attributes:
        passed: Atoms that met the confidence threshold.
        filtered: Atoms that fell below the threshold.
    """

    passed: list[Atom] = field(default_factory=list)
    filtered: list[Atom] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total number of input atoms."""
        return len(self.passed) + len(self.filtered)

    @property
    def passed_count(self) -> int:
        """Number of atoms that passed the filter."""
        return len(self.passed)

    @property
    def filtered_count(self) -> int:
        """Number of atoms filtered out."""
        return len(self.filtered)


def confidence_filter(
    atoms: list[Atom],
    threshold: float = _DEFAULT_THRESHOLD,
) -> FilterResult:
    """Filter atoms by confidence score.

    Args:
        atoms: List of extracted Atom objects.
        threshold: Minimum confidence to pass (default 0.7).

    Returns:
        FilterResult with passed and filtered atom lists.
    """
    result = FilterResult()
    for atom in atoms:
        if atom.confidence >= threshold:
            result.passed.append(atom)
        else:
            result.filtered.append(atom)

    logger.info(
        "Confidence filter (threshold=%.2f): %d passed, %d filtered of %d total",
        threshold,
        result.passed_count,
        result.filtered_count,
        result.total,
    )
    return result
