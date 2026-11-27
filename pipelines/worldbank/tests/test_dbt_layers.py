"""dbt layer dependencies (ADR-0026, ADR-0027): a model reads only the layer directly below.

Only intermediate models may also read their own layer, so shared logic is written once.

A model's layer is the folder it lives in under `models/`. Reads are its `ref()` and `source()`
calls; refs to seeds are allowed where the table below says so.
"""

import re
from pathlib import Path

import pytest

MODELS = Path(__file__).parents[1] / "dbt" / "models"
SEEDS = Path(__file__).parents[1] / "dbt" / "seeds"

MAY_READ = {
    "staging": {"source"},
    "intermediate": {"staging", "intermediate", "seed"},
    "marts": {"intermediate"},
    "reporting": {"marts"},
}

REF = re.compile(r"""\bref\(\s*['"]([\w.]+)['"]\s*\)""")
SOURCE = re.compile(r"""\bsource\(""")


def layer_of(model: Path, models: Path = MODELS) -> str:
    return model.relative_to(models).parts[0]


def model_layers(models: Path = MODELS) -> dict[str, str]:
    return {path.stem: layer_of(path, models) for path in models.rglob("*.sql")}


def reads(model: Path, models: Path = MODELS) -> set[str]:
    """The layers `model` reads from: a model's layer, "seed" or "source"."""
    layers = model_layers(models)
    seeds = {path.stem for path in SEEDS.glob("*.csv")}
    sql = model.read_text(encoding="utf-8")
    found = {"source"} if SOURCE.search(sql) else set()
    for name in REF.findall(sql):
        found.add("seed" if name in seeds else layers.get(name, f"unknown model {name}"))
    return found


def test_every_model_sits_in_a_known_layer() -> None:
    assert set(model_layers().values()) <= set(MAY_READ)


@pytest.mark.parametrize("model", sorted(MODELS.rglob("*.sql")), ids=lambda path: path.stem)
def test_models_read_only_what_their_layer_allows(model: Path) -> None:
    allowed = MAY_READ[layer_of(model)]

    assert reads(model) <= allowed, f"{model.stem} ({layer_of(model)}) may read only {allowed}"


def test_a_mart_reading_staging_is_caught(tmp_path: Path) -> None:
    models = tmp_path / "models"
    (models / "staging").mkdir(parents=True)
    (models / "marts").mkdir()
    (models / "staging" / "stg_x.sql").write_text("SELECT 1 FROM {{ source('s', 't') }}")
    mart = models / "marts" / "dim_x.sql"
    mart.write_text("SELECT * FROM {{ ref('stg_x') }}")

    assert reads(mart, models) == {"staging"}
    assert not reads(mart, models) <= MAY_READ["marts"]


def test_a_mart_reading_another_mart_is_caught(tmp_path: Path) -> None:
    models = tmp_path / "models"
    (models / "marts").mkdir(parents=True)
    (models / "marts" / "dim_x.sql").write_text("SELECT 1")
    fact = models / "marts" / "fct_x.sql"
    fact.write_text("SELECT * FROM {{ ref('dim_x') }}")

    assert not reads(fact, models) <= MAY_READ["marts"]
