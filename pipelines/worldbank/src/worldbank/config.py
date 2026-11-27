"""Pipeline configuration: reads `config.yml` into the validated configuration models (NFR-4).

The models belong to the source they describe (`worldbank.source.config`); this module
only loads them, so nothing in `source/` depends on the top level.
"""

from pathlib import Path

import yaml

from worldbank.source.config import Config

__all__ = ["Config", "load_config"]


def load_config(path: Path) -> Config:
    """Read and validate a YAML configuration file."""
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Config.model_validate(raw)
