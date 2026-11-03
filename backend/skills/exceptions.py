class UnknownSkillError(Exception):
    """The skill string does not resolve to any canonical skill (REQ-F1-05)."""

    def __init__(self, raw: str, suggestions: list[tuple[int, str]]):
        super().__init__(f"Unknown skill: {raw!r}")
        self.raw = raw
        self.suggestions = suggestions
