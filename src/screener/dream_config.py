"""드림팀 지표 설정 로더.

박문환 드림팀 지표의 모든 파라미터를 YAML 파일에서 읽어 관리한다.

환경변수:
    DREAM_INDEX_CONFIG_PATH: YAML 파일 경로
        (기본값: 프로젝트 루트의 'dream-index-config.yaml')

YAML 스키마 (indicators 하위 각 섹션은 생략 가능, 생략 시 기본값):

    indicators:
      dmi:
        period: 14
        lookback_days: 5
      stochastic:
        k: 14
        d: 3
        slowing: 3
        lookback_days: 5
      chaikin:
        fast: 3
        slow: 10
        lookback_days: 5
      macd:
        fast: 12
        slow: 26
        signal: 9
      demark:
        lookback: 4
        lookback_days: 5

    report:
      min_strength: 2
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("dream-index-config.yaml")
CONFIG_ENV_VAR = "DREAM_INDEX_CONFIG_PATH"


@dataclass(frozen=True)
class DMIConfig:
    """DMI(Directional Movement Index) 지표 설정."""

    period: int = 14
    lookback_days: int = 5


@dataclass(frozen=True)
class StochasticConfig:
    """스토캐스틱 오실레이터 지표 설정."""

    k: int = 14
    d: int = 3
    slowing: int = 3
    lookback_days: int = 5


@dataclass(frozen=True)
class ChaikinConfig:
    """채킨 오실레이터 지표 설정."""

    fast: int = 3
    slow: int = 10
    lookback_days: int = 5


@dataclass(frozen=True)
class MACDConfig:
    """MACD 오실레이터(주봉) 지표 설정."""

    fast: int = 12
    slow: int = 26
    signal: int = 9


@dataclass(frozen=True)
class DeMarkConfig:
    """드마크 TD 카운팅 지표 설정 (보완 지표)."""

    lookback: int = 4
    lookback_days: int = 5


@dataclass(frozen=True)
class ReportIndexConfig:
    """드림팀 리포트 필터 설정."""

    min_strength: int = 2


@dataclass(frozen=True)
class DreamIndexConfig:
    """드림팀 지표 전체 설정.

    하위 지표별 파라미터와 리포트 필터 임계값을 포함한다.
    """

    dmi: DMIConfig = field(default_factory=DMIConfig)
    stochastic: StochasticConfig = field(default_factory=StochasticConfig)
    chaikin: ChaikinConfig = field(default_factory=ChaikinConfig)
    macd: MACDConfig = field(default_factory=MACDConfig)
    demark: DeMarkConfig = field(default_factory=DeMarkConfig)
    report: ReportIndexConfig = field(default_factory=ReportIndexConfig)


def _resolve_config_path(path: Path | str | None) -> Path:
    """설정 파일 경로를 결정한다.

    우선순위: 명시적 인자 > 환경변수 > 기본 경로.
    """
    if path is not None:
        return Path(path)
    env_path = os.environ.get(CONFIG_ENV_VAR)
    if env_path:
        return Path(env_path)
    return DEFAULT_CONFIG_PATH


def _safe_section(data: dict[str, Any], key: str) -> dict[str, Any]:
    """중첩 섹션을 안전하게 꺼낸다 (None은 빈 dict로 처리)."""
    section = data.get(key)
    return section if isinstance(section, dict) else {}


def load_dream_index_config(
    path: Path | str | None = None,
) -> DreamIndexConfig:
    """드림팀 지표 설정을 로드한다.

    파일이 존재하지 않으면 경고 로그 후 기본값을 반환한다.
    YAML 파싱 오류 시에도 기본값으로 폴백한다.
    """
    resolved = _resolve_config_path(path)

    if not resolved.exists():
        logger.info(
            "드림팀 설정 파일 없음 — 기본값 사용: %s",
            resolved,
        )
        return DreamIndexConfig()

    try:
        with resolved.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning(
            "드림팀 설정 파일 로드 실패 (%s): %s — 기본값 사용",
            resolved,
            exc,
        )
        return DreamIndexConfig()

    indicators = _safe_section(raw, "indicators")

    try:
        return DreamIndexConfig(
            dmi=DMIConfig(**_safe_section(indicators, "dmi")),
            stochastic=StochasticConfig(**_safe_section(indicators, "stochastic")),
            chaikin=ChaikinConfig(**_safe_section(indicators, "chaikin")),
            macd=MACDConfig(**_safe_section(indicators, "macd")),
            demark=DeMarkConfig(**_safe_section(indicators, "demark")),
            report=ReportIndexConfig(**_safe_section(raw, "report")),
        )
    except TypeError as exc:
        logger.warning(
            "드림팀 설정 파일에 알 수 없는 키 포함 (%s): %s — 기본값 사용",
            resolved,
            exc,
        )
        return DreamIndexConfig()
