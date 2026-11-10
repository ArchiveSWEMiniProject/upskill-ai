"""PR-3 completion policy pending PR-4 evidence integration."""

from collections.abc import Callable

EvidenceRequirement = Callable[[int], bool | None]


def temporary_evidence_requirement(_resource_id: int) -> bool:
    """Allow self-reported completion for every eligible resource for now."""
    return False


def get_completion_policy() -> EvidenceRequirement:
    """Use the temporary waiver until the catalogue evidence policy is available.

    True requires evidence, False explicitly exempts, None means unavailable.
    """
    return temporary_evidence_requirement
