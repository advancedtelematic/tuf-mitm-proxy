

class Error(Exception):
    """The base class for proxy errors."""
    pass


class ContentTypeError(Error):
    def __init__(self, expected: str, got: str) -> None:
        self.expected = expected
        self.got = got

    def __str__(self) -> str:
        return f"Expected content-type {self.expected}, got {self.got}"


class InvalidKeyIdError(Error):
    def __init__(self, keyid: str) -> None:
        self.keyid = keyid

    def __str__(self) -> str:
        return f"Invalid keyid: {self.keyid}"


class MissingFieldError(Error):
    def __init__(self, name: str, field: str) -> None:
        self.name = name
        self.field = field

    def __str__(self) -> str:
        return f"{self.name} missing field: {self.field}"


class UnknownRoleError(Error):
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return f"unknown role: {self.name}"