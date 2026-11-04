class ResourceNotFoundError(Exception):
    """The requested resource does not exist."""


class InvalidStoryError(Exception):
    """A stored story cannot be assembled into a complete story."""
