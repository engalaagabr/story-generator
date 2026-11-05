"""Explicit model registration for migrations and test schema creation.

Register new feature models here. Importing them does not open a connection.
"""

from app.db.base import Base
from app.modules.jobs.models import StoryJob
from app.modules.stories.models import Story, StoryNode

__all__ = ["Base", "Story", "StoryNode", "StoryJob"]
