class SpaceError(Exception):
    """Base exception for Space-OS domain errors."""

    pass


class ChannelNotFoundError(SpaceError):
    """Raised when a specified channel cannot be found."""

    pass


class MigrationError(SpaceError):
    """Raised when a database migration fails."""

    pass


class ProtocolError(SpaceError):
    """Raised when protocol operations fail."""

    pass
