"""Tests for Rubricon configuration loading."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from rubricon import RubriconConfig
from rubricon.config import local_ollama, production, quick


def test_defaults_construct_cleanly() -> None:
    cfg = RubriconConfig()
    assert cfg.generator.model == "gpt-4o"
    assert cfg.criteria.n == 5
    assert cfg.convergence.threshold == 0.6
    assert cfg.reattention.strategy == "focal"
    assert cfg.reattention.alpha == 2.0
    assert len(cfg.evaluators) == 1
    assert cfg.evaluators[0].type == "llm_judge"


def test_threshold_validation() -> None:
    with pytest.raises(ValueError):
        RubriconConfig.from_dict({"convergence": {"threshold": 1.5}})


def test_dict_loading() -> None:
    cfg = RubriconConfig.from_dict({
        "generator": {"model": "gpt-4o-mini", "temperature": 0.2},
        "criteria": {"n": 3, "dynamic": False},
        "reattention": {"strategy": "uniform", "enabled": False},
    })
    assert cfg.generator.model == "gpt-4o-mini"
    assert cfg.generator.temperature == 0.2
    assert cfg.criteria.n == 3
    assert cfg.criteria.dynamic is False
    assert cfg.reattention.strategy == "uniform"
    assert cfg.reattention.enabled is False


def test_yaml_loading_and_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "cfg.yaml"
    p.write_text(
        """
generator:
  model: claude-sonnet-4-20250514
  temperature: 0.5
criteria:
  n: 4
"""
    )
    cfg = RubriconConfig.from_yaml(p)
    assert cfg.generator.model == "claude-sonnet-4-20250514"
    assert cfg.criteria.n == 4

    out = tmp_path / "out.yaml"
    cfg.to_yaml(out)
    cfg2 = RubriconConfig.from_yaml(out)
    assert cfg.model_dump() == cfg2.model_dump()


def test_env_overrides() -> None:
    os.environ["RUBRICON_GENERATOR__MODEL"] = "gpt-4o-mini"
    os.environ["RUBRICON_CRITERIA__N"] = "7"
    os.environ["RUBRICON_DETERMINISTIC"] = "true"
    try:
        cfg = RubriconConfig.load()
        assert cfg.generator.model == "gpt-4o-mini"
        assert cfg.criteria.n == 7
        assert cfg.deterministic is True
    finally:
        del os.environ["RUBRICON_GENERATOR__MODEL"]
        del os.environ["RUBRICON_CRITERIA__N"]
        del os.environ["RUBRICON_DETERMINISTIC"]


def test_layered_resolution_kwargs_win(tmp_path: Path) -> None:
    """defaults < file < env < kwargs — kwargs always last."""
    p = tmp_path / "cfg.yaml"
    p.write_text("generator:\n  model: file-model\n")
    os.environ["RUBRICON_GENERATOR__MODEL"] = "env-model"
    try:
        cfg = RubriconConfig.load(p, generator={"model": "kwargs-model"})
        assert cfg.generator.model == "kwargs-model"
    finally:
        del os.environ["RUBRICON_GENERATOR__MODEL"]


def test_override_returns_new_config() -> None:
    cfg = RubriconConfig()
    cfg2 = cfg.override(deterministic=True)
    assert cfg.deterministic is False
    assert cfg2.deterministic is True


def test_deterministic_propagates_seed() -> None:
    cfg = RubriconConfig.from_dict({
        "deterministic": True,
        "evaluator": {"model": "gpt-4o"},
    })
    assert cfg.generator.seed == 42
    assert cfg.evaluator is not None
    assert cfg.evaluator.seed == 42


def test_presets_construct() -> None:
    assert quick("gpt-4o-mini").generator.model == "gpt-4o-mini"
    ollama = local_ollama()
    assert ollama.generator.model.startswith("ollama/")
    assert ollama.evaluator is not None
    prod = production("gpt-4o", "claude-sonnet-4-20250514")
    assert prod.budget.max_cost_usd == 1.0
    assert prod.cache.enabled is True
