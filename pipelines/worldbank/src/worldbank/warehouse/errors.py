"""The one error type every warehouse failure shares, so callers can catch it in one place."""


class WarehouseError(Exception):
    """A build can't be loaded or published; the live warehouse is unchanged (ADR-0007)."""
