"""Read-only access to the skill taxonomy.

The taxonomy tables are written only by M4 (architecture rule R5) and are
shared reference data that every module reads. This module reads them with
lightweight table definitions rather than importing M4's code (rule R2), and
never writes to them.
"""

from sqlalchemy import column, select, table
from sqlalchemy.orm import Session

from backend.taxonomy.resolver import SkillResolver, build_alias_index

_skill = table("skill", column("skill_id"), column("skill_name"))
_skill_alias = table("skill_alias", column("skill_id"), column("alias_text"))


class TaxonomyReader:
    def __init__(self, session: Session):
        self._session = session
        self._names: dict[int, str] | None = None

    def names(self) -> dict[int, str]:
        """Canonical skill names by id."""
        if self._names is None:
            rows = self._session.execute(select(_skill.c.skill_id, _skill.c.skill_name))
            self._names = {skill_id: name for skill_id, name in rows}
        return self._names

    def resolver(self) -> SkillResolver:
        aliases = self._session.execute(select(_skill_alias.c.skill_id, _skill_alias.c.alias_text))
        return SkillResolver(build_alias_index(self.names().items(), aliases))
