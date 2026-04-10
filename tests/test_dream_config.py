"""드림팀 지표 설정 로더 테스트."""

from pathlib import Path

import pytest

from src.screener.dream_config import (
    CONFIG_ENV_VAR,
    DMIConfig,
    DeMarkConfig,
    DreamIndexConfig,
    MACDConfig,
    ReportIndexConfig,
    StochasticConfig,
    load_dream_index_config,
)


class TestDefaults:
    """설정 파일 부재 시 기본값을 반환해야 한다."""

    def test_nonexistent_path_returns_defaults(self, tmp_path: Path) -> None:
        missing = tmp_path / "no-such-file.yaml"
        config = load_dream_index_config(missing)
        assert config == DreamIndexConfig()
        assert config.dmi.period == 14
        assert config.stochastic.k == 14
        assert config.chaikin.fast == 3
        assert config.macd.fast == 12
        assert config.demark.lookback == 4
        assert config.report.min_strength == 2

    def test_defaults_are_consistent(self) -> None:
        assert DMIConfig().lookback_days == 5
        assert StochasticConfig().slowing == 3
        assert MACDConfig().signal == 9
        assert DeMarkConfig().lookback_days == 5
        assert ReportIndexConfig().min_strength == 2


class TestYamlLoading:
    """YAML 파일에서 값을 정상적으로 읽어야 한다."""

    def test_full_override(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "dream.yaml"
        yaml_path.write_text(
            """
indicators:
  dmi:
    period: 21
    lookback_days: 10
  stochastic:
    k: 9
    d: 5
    slowing: 2
    lookback_days: 7
  chaikin:
    fast: 5
    slow: 15
    lookback_days: 3
  macd:
    fast: 8
    slow: 17
    signal: 6
  demark:
    lookback: 6
    lookback_days: 4
report:
  min_strength: 4
""",
            encoding="utf-8",
        )
        config = load_dream_index_config(yaml_path)

        assert config.dmi.period == 21
        assert config.dmi.lookback_days == 10
        assert config.stochastic.k == 9
        assert config.chaikin.slow == 15
        assert config.macd.signal == 6
        assert config.demark.lookback == 6
        assert config.report.min_strength == 4

    def test_partial_override_keeps_defaults(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "partial.yaml"
        yaml_path.write_text(
            """
indicators:
  dmi:
    period: 20
report:
  min_strength: 1
""",
            encoding="utf-8",
        )
        config = load_dream_index_config(yaml_path)
        assert config.dmi.period == 20
        assert config.dmi.lookback_days == 5  # default preserved
        assert config.stochastic.k == 14  # default preserved
        assert config.report.min_strength == 1

    def test_empty_file_returns_defaults(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "empty.yaml"
        yaml_path.write_text("", encoding="utf-8")
        assert load_dream_index_config(yaml_path) == DreamIndexConfig()

    def test_unknown_keys_fallback_to_defaults(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "bad.yaml"
        yaml_path.write_text(
            """
indicators:
  dmi:
    period: 14
    unknown_field: 999
""",
            encoding="utf-8",
        )
        # 알 수 없는 키가 있으면 안전하게 기본값으로 폴백
        assert load_dream_index_config(yaml_path) == DreamIndexConfig()

    def test_malformed_yaml_fallback_to_defaults(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "malformed.yaml"
        yaml_path.write_text("indicators: [unclosed", encoding="utf-8")
        assert load_dream_index_config(yaml_path) == DreamIndexConfig()


class TestEnvVarResolution:
    """환경변수로 설정 파일 경로를 지정할 수 있어야 한다."""

    def test_env_var_is_used_when_no_explicit_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        yaml_path = tmp_path / "env-dream.yaml"
        yaml_path.write_text(
            "report:\n  min_strength: 3\n",
            encoding="utf-8",
        )
        monkeypatch.setenv(CONFIG_ENV_VAR, str(yaml_path))
        config = load_dream_index_config()
        assert config.report.min_strength == 3

    def test_explicit_path_wins_over_env_var(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        env_yaml = tmp_path / "env.yaml"
        env_yaml.write_text(
            "report:\n  min_strength: 1\n",
            encoding="utf-8",
        )
        explicit_yaml = tmp_path / "explicit.yaml"
        explicit_yaml.write_text(
            "report:\n  min_strength: 4\n",
            encoding="utf-8",
        )
        monkeypatch.setenv(CONFIG_ENV_VAR, str(env_yaml))
        config = load_dream_index_config(explicit_yaml)
        assert config.report.min_strength == 4
