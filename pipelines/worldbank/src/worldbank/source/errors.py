"""The one error type every extract failure shares, so callers can catch it in one place."""


class ExtractError(Exception):
    """The extract can't produce a valid run; nothing is committed (ADR-0007)."""
