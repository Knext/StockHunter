from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DMIResult:
    """DMI (Directional Movement Index) 계산 결과.

    Attributes:
        date: 거래일
        plus_di: +DI 값 (양의 방향 지표)
        minus_di: -DI 값 (음의 방향 지표)
        adx: ADX 값 (평균 방향성 지수)
        buy_signal: 매수 신호 여부
            (-DI가 ADX를 30 이상에서 하향 돌파 + 3일 내 ADX 하락 전환)
    """

    date: date
    plus_di: float | None
    minus_di: float | None
    adx: float | None
    buy_signal: bool


@dataclass(frozen=True)
class StochasticResult:
    """스토캐스틱 오실레이터 계산 결과.

    Attributes:
        date: 거래일
        k: Slow %K 값
        d: Slow %D 값
        buy_reinforcement: 매수 강화 여부 (%K가 80을 상향 돌파)
    """

    date: date
    k: float | None
    d: float | None
    buy_reinforcement: bool


@dataclass(frozen=True)
class ChaikinResult:
    """채킨 오실레이터 계산 결과.

    Attributes:
        date: 거래일
        co_value: 채킨 오실레이터 값 (ADL의 단기EMA - 장기EMA)
        buy_signal: 0선 상향 돌파 여부
    """

    date: date
    co_value: float | None
    buy_signal: bool


@dataclass(frozen=True)
class MACDOscResult:
    """MACD 오실레이터 계산 결과 (주봉 기준).

    Attributes:
        date: 거래일
        macd: MACD선 (단기EMA - 장기EMA)
        signal: 시그널선 (MACD의 EMA)
        oscillator: 오실레이터/히스토그램 (MACD - Signal)
        buy_signal: 주봉 오실레이터 호전 여부
            (양전환 또는 상승 전환)
    """

    date: date
    macd: float | None
    signal: float | None
    oscillator: float | None
    buy_signal: bool


@dataclass(frozen=True)
class DeMarkResult:
    """드마크 (TD Sequential) 계산 결과.

    Attributes:
        date: 거래일
        setup_count: Setup 카운트 (0-9)
        countdown_count: Countdown 카운트 (0-13)
        setup_complete: Setup 9 완성 여부
        countdown_complete: Countdown 13 완성 여부
    """

    date: date
    setup_count: int
    countdown_count: int
    setup_complete: bool
    countdown_complete: bool
