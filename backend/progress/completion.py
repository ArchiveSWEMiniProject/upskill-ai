"""PR-3 completion boundary; the team has not supplied resource evidence policy.

Unknown policy is not an exemption. PR-4 will provide evidence submission and
validation; PR-5/6 will handle skill updates and recommendation invalidation.
"""

from collections.abc import Callable

EvidenceRequirement = Callable[[int], bool | None]


def unresolved_evidence_requirement(resource_id: int) -> bool | None:
    """No catalogue field/provider exists yet; never guess based on resource type."""
    return None


def get_completion_policy() -> EvidenceRequirement:
    """Integration seam for the future team-approved server-side policy provider.

    True requires evidence, False explicitly exempts, None means unavailable.
    This is deliberately unbound in production, not a fake catalogue adapter.
    """
    return unresolved_evidence_requirement
