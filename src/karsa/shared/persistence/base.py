from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base

from .naming import naming_convention

# Single metadata registry with consistent naming conventions
metadata = MetaData(naming_convention=naming_convention)

# Base class for all declarative models
Base = declarative_base(metadata=metadata)
