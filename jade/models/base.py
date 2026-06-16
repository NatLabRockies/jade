"""Defines JADE base model"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from jade.utils.utils import load_data


class JadeBaseModel(BaseModel):
    """Base class for JADE models."""

    model_config = ConfigDict(
        title="JadeBaseModel",
        str_strip_whitespace=True,
        validate_assignment=True,
        validate_default=True,
        extra="forbid",
        use_enum_values=False,
        populate_by_name=True,
    )

    @classmethod
    def load(cls, path: Path):
        """Load a model from a file."""
        return cls(**load_data(path))
