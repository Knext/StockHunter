"""Pydantic v2 응답/요청 스키마 정의."""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """통일된 API 응답 형식."""

    success: bool
    data: T | None = None
    error: str | None = None
    meta: dict | None = None


# --- Screen 관련 ---


class ScreenResult(BaseModel):
    """드림팀 스크리닝 결과 단일 항목."""

    code: str
    name: str
    market: str
    date: str
    dmi_signal: bool
    stochastic_signal: bool
    chaikin_signal: bool
    macd_signal: bool
    demark_signal: bool
    signal_strength: int
    signal_grade: str


class ScreenMeta(BaseModel):
    """스크리닝 메타 정보."""

    total: int
    screened_at: str
    market: str


# --- Stock Detail 관련 ---


class StockInfoSchema(BaseModel):
    """종목 정보."""

    code: str
    name: str
    market: str
    sector: str


class DMIIndicator(BaseModel):
    """DMI 지표 상세."""

    plus_di: float | None
    minus_di: float | None
    adx: float | None
    buy_signal: bool


class StochasticIndicator(BaseModel):
    """스토캐스틱 지표 상세."""

    k: float | None
    d: float | None
    buy_reinforcement: bool


class ChaikinIndicator(BaseModel):
    """채킨 지표 상세."""

    value: float | None
    buy_signal: bool


class MACDIndicator(BaseModel):
    """MACD 지표 상세."""

    macd: float | None
    signal: float | None
    oscillator: float | None
    buy_signal: bool


class DeMarkIndicator(BaseModel):
    """드마크 지표 상세."""

    setup_count: int
    countdown_count: int
    setup_complete: bool


class IndicatorsDetail(BaseModel):
    """5개 지표 상세."""

    dmi: DMIIndicator
    stochastic: StochasticIndicator
    chaikin: ChaikinIndicator
    macd: MACDIndicator
    demark: DeMarkIndicator


class DreamTeamSummary(BaseModel):
    """드림팀 종합 결과."""

    signal_strength: int
    signal_grade: str


class StockDetail(BaseModel):
    """개별 종목 상세 지표."""

    info: StockInfoSchema
    indicators: IndicatorsDetail
    dream_team: DreamTeamSummary


# --- Indicator Config 관련 ---


class DMIConfig(BaseModel):
    """DMI 설정."""

    period: int = 14


class StochasticConfig(BaseModel):
    """스토캐스틱 설정."""

    k_period: int = 14
    d_period: int = 3
    slowing: int = 3


class ChaikinConfig(BaseModel):
    """채킨 설정."""

    fast_period: int = 3
    slow_period: int = 10


class MACDConfig(BaseModel):
    """MACD 설정."""

    fast: int = 12
    slow: int = 26
    signal: int = 9


class DeMarkConfig(BaseModel):
    """드마크 설정."""

    lookback: int = 4


class ScreeningConfig(BaseModel):
    """스크리닝 설정."""

    lookback_days: int = 5
    default_days: int = 200


class IndicatorConfigResponse(BaseModel):
    """지표 설정 전체."""

    dmi: DMIConfig = Field(default_factory=DMIConfig)
    stochastic: StochasticConfig = Field(default_factory=StochasticConfig)
    chaikin: ChaikinConfig = Field(default_factory=ChaikinConfig)
    macd: MACDConfig = Field(default_factory=MACDConfig)
    demark: DeMarkConfig = Field(default_factory=DeMarkConfig)
    screening: ScreeningConfig = Field(default_factory=ScreeningConfig)
