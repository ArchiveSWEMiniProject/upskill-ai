"""Catalogue validation and canonical skill resolution.

Complies with:
- REQ-F4-08: Validate catalogue fields (TC-F4-07, TC-F4-08)
- BR-01: Every catalogue resource must be associated with at least one canonical skill tag
- CONTRACTS.md §2: Lowercased, whitespace-trimmed alias and canonical matching
"""

import difflib

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.catalogue.models import Skill, SkillAlias
from backend.catalogue.schemas import SkillTagInput


def resolve_canonical_skill(
    tag: SkillTagInput,
    db: Session,
) -> tuple[int, str]:
    """Resolve a skill tag to its canonical skill_id and skill_name.

    Resolves by:
    1. Direct skill_id if provided.
    2. Exact canonical skill_name (case-insensitive, trimmed).
    3. Alias in skill_alias table (case-insensitive, trimmed).

    If unresolvable, raises HTTPException(400) containing closest matching suggestions (TC-F4-08).
    """
    all_skills = db.query(Skill).all()
    canonical_names = [s.skill_name for s in all_skills]
    skill_map_by_id = {s.skill_id: s.skill_name for s in all_skills}
    skill_map_by_name = {s.skill_name.strip().lower(): s for s in all_skills}

    # 1. By skill_id
    if tag.skill_id is not None:
        if tag.skill_id in skill_map_by_id:
            return tag.skill_id, skill_map_by_id[tag.skill_id]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Skill ID {tag.skill_id} does not correspond to a canonical skill in the taxonomy."
            ),
        )

    # 2. By skill_name
    if not tag.skill_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill tag must provide either a skill_id or skill_name.",
        )

    cleaned_name = tag.skill_name.strip().lower()

    # Exact canonical match
    if cleaned_name in skill_map_by_name:
        matched = skill_map_by_name[cleaned_name]
        return matched.skill_id, matched.skill_name

    # Check alias in skill_alias table
    alias_match = (
        db.query(SkillAlias)
        .filter(SkillAlias.alias_text.ilike(cleaned_name))
        .first()
    )
    if alias_match:
        canonical_skill = db.query(Skill).filter(Skill.skill_id == alias_match.skill_id).first()
        if canonical_skill:
            return canonical_skill.skill_id, canonical_skill.skill_name

    # Not found -> find close matches using difflib for suggestions (TC-F4-08)
    suggestions = difflib.get_close_matches(tag.skill_name, canonical_names, n=3, cutoff=0.3)
    error_msg = (
        f"Skill '{tag.skill_name}' does not correspond to a canonical skill in the taxonomy."
    )
    if suggestions:
        error_msg += f" Closest matching canonical skills: {', '.join(suggestions)}."

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=error_msg,
    )
