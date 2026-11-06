"""Errors raised while building a student's gap (RM-3). The route turns them into
HTTP statuses; the messages are safe to show to the student."""


class GapError(Exception):
    message = "The skill gap could not be computed"

    def __init__(self) -> None:
        super().__init__(self.message)


class NoProfileError(GapError):
    message = "Create your profile before viewing your skill gap"


class NoTargetRoleError(GapError):
    message = "Choose a target role to see your skill gap"
