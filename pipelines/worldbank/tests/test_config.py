from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from worldbank.config import Config, load_config

PIPELINE_CONFIG = Path(__file__).parents[1] / "config.yml"


def _valid() -> dict[str, Any]:
    return {
        "api": {
            "base_url": "https://api.worldbank.org/v2",
            "source": 2,
            "per_page": 1000,
            "timeout": {"connect_seconds": 10, "read_seconds": 30},
            "retry": {"attempts": 5, "initial_backoff_seconds": 1, "max_backoff_seconds": 30},
        },
        "scope": {
            "countries": ["BRA", "IND"],
            "indicators": ["SP.POP.TOTL"],
            "years": {"start": 2018, "end": 2024},
        },
    }


def test_pipeline_config_matches_the_brief() -> None:
    config = load_config(PIPELINE_CONFIG)

    assert config.scope.countries == [
        "BRA", "CAN", "DEU", "GBR", "IND", "JPN", "MEX", "USA", "ZAF",
    ]  # fmt: skip
    assert config.scope.indicators == [
        "SP.POP.TOTL", "NY.GDP.MKTP.CD", "NY.GDP.PCAP.CD", "SP.DYN.LE00.IN",
    ]  # fmt: skip
    assert list(config.scope.years.as_range()) == list(range(2018, 2025))
    assert config.api.source == 2


def test_load_config_reads_yaml(tmp_path: Path) -> None:
    path = tmp_path / "config.yml"
    path.write_text(yaml.safe_dump(_valid()))

    assert load_config(path).scope.countries == ["BRA", "IND"]


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("scope", "countries", ["bra"]),
        ("scope", "countries", ["BRAZIL"]),
        ("scope", "countries", ["BRA", "BRA"]),
        ("scope", "countries", []),
        ("scope", "indicators", ["not a code"]),
        ("scope", "indicators", ["SP/POP"]),
        ("scope", "indicators", [".SP.POP"]),
        ("scope", "indicators", ["SP..POP"]),
        ("scope", "indicators", ["SP.POP.TOTL", "SP.POP.TOTL"]),
        ("scope", "years", {"start": 2024, "end": 2018}),
        ("api", "per_page", 0),
        ("api", "base_url", "not-a-url"),
    ],
)
def test_invalid_values_are_rejected(section: str, key: str, value: object) -> None:
    raw = _valid()
    raw[section][key] = value

    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_unknown_keys_are_rejected() -> None:
    raw = _valid()
    raw["scope"]["countrys"] = ["BRA"]

    with pytest.raises(ValidationError, match="countrys"):
        Config.model_validate(raw)


def test_retry_backoff_bounds_are_checked() -> None:
    raw = _valid()
    raw["api"]["retry"] = {"attempts": 3, "initial_backoff_seconds": 10, "max_backoff_seconds": 1}

    with pytest.raises(ValidationError, match="max_backoff_seconds"):
        Config.model_validate(raw)


@pytest.mark.parametrize(
    ("section", "key", "value", "valid"),
    [
        ("scope", "years", {"start": 1960, "end": 1960}, True),
        ("scope", "years", {"start": 1959, "end": 2024}, False),
        ("scope", "years", {"start": 2018, "end": 2101}, False),
        ("api", "per_page", 32_500, True),
        ("api", "per_page", 32_501, False),
        ("api", "source", 0, False),
        (
            "api",
            "retry",
            {"attempts": 0, "initial_backoff_seconds": 1, "max_backoff_seconds": 1},
            False,
        ),
        (
            "api",
            "retry",
            {"attempts": 1, "initial_backoff_seconds": 2, "max_backoff_seconds": 2},
            True,
        ),
        (
            "api",
            "retry",
            {"attempts": 1, "initial_backoff_seconds": -1, "max_backoff_seconds": 2},
            False,
        ),
        ("api", "timeout", {"connect_seconds": 0, "read_seconds": 30}, False),
    ],
)
def test_boundaries(section: str, key: str, value: object, valid: bool) -> None:
    raw = _valid()
    raw[section][key] = value

    if valid:
        Config.model_validate(raw)
    else:
        with pytest.raises(ValidationError):
            Config.model_validate(raw)


def test_config_is_immutable() -> None:
    config = Config.model_validate(_valid())

    with pytest.raises(ValidationError):
        config.scope.countries = ["USA"]


def test_empty_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "config.yml"
    path.write_text("")

    with pytest.raises(ValidationError):
        load_config(path)


@pytest.mark.parametrize(
    "code",
    [
        "SP.POP.TOTL",
        "NY.GDP.PCAP.CD",
        "GD_WBL_OVL_ENF",
        "SH_UHC_FH40_FURTHER",
        "per_allsp.adq_pop_tot",
    ],
)
def test_every_shape_of_real_indicator_code_is_accepted(code: str) -> None:
    """Real World Development Indicators codes, including underscores and lower case."""
    raw = _valid()
    raw["scope"]["indicators"] = [code]

    assert Config.model_validate(raw).scope.indicators == [code]
