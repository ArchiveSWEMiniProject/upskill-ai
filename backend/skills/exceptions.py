class UnknownSkillError(Exception):
    """The skill string does not resolve to any canonical skill (REQ-F1-05)."""

    def __init__(
        self,
        raw: str,
        suggestions: list[tuple[int, str]],
        unresolved_id: int | None = None,
    ):
        super().__init__(f"Unknown skill: {raw!r}")
        self.raw = raw
        self.suggestions = suggestions
        self.unresolved_id = unresolved_id


class UnresolvedSkillNotFoundError(Exception):
    """No open unresolved skill with that id on the caller's profile."""

    message = "Unresolved skill not found"


class NotACanonicalSkillError(Exception):
    """The skill chosen to map to is not in the taxonomy."""

    message = "Unknown canonical skill"
