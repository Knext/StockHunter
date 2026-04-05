"""스토캐스틱 오실레이터 (Stochastic Oscillator) 계산 모듈.

박문환 드림팀의 두 번째 지표 - "매수 강화 확인".
George Lane 개발.

Slow Stochastic (14, 3, 3) 기본 설정.
매수 강화: %K가 80을 상향 돌파.
"""

from src.indicators.types import StochasticResult
from src.types.ohlcv import OHLCV


def _raw_k(
    data: tuple[OHLCV, ...],
    index: int,
    k_period: int,
) -> float | None:
    """Raw %K 계산.

    %K = 100 * (Close - Lowest Low) / (Highest High - Lowest Low)
    """
    start = index - k_period + 1
    if start < 0:
        return None

    close = data[index].close
    if close is None:
        return None

    highs: list[float] = []
    lows: list[float] = []

    for i in range(start, index + 1):
        if data[i].high is None or data[i].low is None:
            return None
        highs.append(data[i].high)  # type: ignore[arg-type]
        lows.append(data[i].low)  # type: ignore[arg-type]

    highest = max(highs)
    lowest = min(lows)

    if highest == lowest:
        return None

    return 100.0 * (close - lowest) / (highest - lowest)


def _sma(values: list[float | None], period: int) -> float | None:
    """단순 이동평균. None이 포함되면 None 반환."""
    if len(values) < period:
        return None

    window = values[-period:]
    if any(v is None for v in window):
        return None

    return sum(v for v in window if v is not None) / period


def calculate_stochastic(
    data: tuple[OHLCV, ...],
    k_period: int = 14,
    d_period: int = 3,
    slowing: int = 3,
) -> tuple[StochasticResult, ...]:
    """Slow Stochastic 오실레이터를 계산한다.

    Slow %K = SMA(Raw %K, slowing)
    Slow %D = SMA(Slow %K, d_period)

    Args:
        data: OHLCV 데이터 (날짜 오름차순)
        k_period: %K 기간 (기본 14)
        d_period: %D 기간 (기본 3)
        slowing: 슬로잉 기간 (기본 3)

    Returns:
        StochasticResult 튜플
    """
    min_required = k_period + slowing + d_period - 2
    if len(data) < min_required:
        return ()

    raw_k_values: list[float | None] = []
    for i in range(len(data)):
        if i < k_period - 1:
            raw_k_values.append(None)
        else:
            raw_k_values.append(_raw_k(data, i, k_period))

    slow_k_values: list[float | None] = []
    for i in range(len(data)):
        if i < k_period + slowing - 2:
            slow_k_values.append(None)
        else:
            window = raw_k_values[i - slowing + 1:i + 1]
            slow_k_values.append(_sma(window, slowing))

    slow_d_values: list[float | None] = []
    for i in range(len(data)):
        if i < k_period + slowing + d_period - 3:
            slow_d_values.append(None)
        else:
            window = slow_k_values[i - d_period + 1:i + 1]
            slow_d_values.append(_sma(window, d_period))

    results: list[StochasticResult] = []
    start_index = k_period + slowing - 2

    for i in range(start_index, len(data)):
        k = slow_k_values[i]
        d = slow_d_values[i]

        buy_reinforcement = False
        if k is not None and i > start_index:
            prev_k = slow_k_values[i - 1]
            if prev_k is not None and prev_k < 80 and k >= 80:
                buy_reinforcement = True

        results.append(StochasticResult(
            date=data[i].date,
            k=k,
            d=d,
            buy_reinforcement=buy_reinforcement,
        ))

    return tuple(results)
