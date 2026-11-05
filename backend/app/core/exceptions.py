"""Application errors with messages safe to show through an API or job status."""


class ApplicationError(Exception):
    """Expected failure with a public message; contains no HTTP or ORM behavior."""


class ResourceNotFoundError(ApplicationError):
    """A requested resource does not exist."""


class InvalidStoryError(ApplicationError):
    """A stored story cannot be assembled."""


class StoryGenerationError(ApplicationError):
    """Generation failed or produced an invalid story."""
