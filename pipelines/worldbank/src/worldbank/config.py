"""Pipeline configuration: reads `config.yml` into validated settings (NFR-4).

The settings models themselves belong to the source they describe (`worldbank.source.settings`).
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from worldbank.source.settings import Api, Scope


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    api: Api
    scope: Scope


def load_config(path: Path) -> Config:
    """Read and validate a YAML configuration file."""
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Config.model_validate(raw)
