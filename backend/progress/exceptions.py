class DomainError(Exception):
    status_code = 400
    code = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class InvalidInputError(DomainError):
    status_code = 422
    code = "invalid_input"


class DependencyUnavailableError(DomainError):
    status_code = 503
    code = "dependency_unavailable"
