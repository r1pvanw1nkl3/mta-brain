class MTABrainError(Exception):
    """Base exception for all mta-brain related errors."""

    pass


class FeedError(MTABrainError):
    """Base exception for feed-related errors."""

    pass


class FeedFetchError(FeedError):
    """Raised when fetching a feed from an external source fails."""

    pass


class FeedParseError(FeedError):
    """Raised when parsing or validating a feed fails."""

    pass


class StorageError(MTABrainError):
    """Base exception for storage-related errors (DB, Redis, etc.)."""

    pass


class DatabaseError(StorageError):
    """Raised when a database operation fails."""

    pass


class CacheError(StorageError):
    """Raised when a cache/Redis operation fails."""

    pass
