"""The one error type every landing-zone failure shares, so callers can catch it in one place."""


class StorageError(Exception):
    """A run can't be written or read as the landing zone's rules require (ADR-0004)."""
