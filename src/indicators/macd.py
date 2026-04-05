"""MACD 오실레이터 계산 모듈.

박문환 드림팀의 네 번째 지표 - "최종 매수 결정".
Gerald Appel 개발.

주봉(Weekly) 기준 MACD 오실레이터 호전을 확인한다.
매수: 오실레이터(히스토그램)가 양전환 또는 상승 전환.
"""

from src.indicators.types import MACDOscResult
from src.types.ohlcv import OHLCV


def _ema_series(
    values: list[float],
    period: int,
) -> list[float | None]:
    """EMA 시리즈 계산.

    Returns:
        입력과 동일 길이의 리스트 (초기 period-1개는 None)
    """
    if len(values) < period:
        return [None] * len(values)

    multiplier = 2.0 / (period + 1)
    result: list[float | None] = [None] * (period - 1)

    sma = sum(values[:period]) / period
    result.append(sma)

    for i in range(period, len(values)):
        prev = result[-1]
        if prev is None:
            result.append(None)
        else:
            ema_val = (values[i] - prev) * multiplier + prev
            result.append(ema_val)

    return result


def calculate_macd_oscillator(
    weekly_data: tuple[OHLCV, ...],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[MACDOscResult, ...]:
    """MACD 오실레이터를 계산한다 (주봉 기준).

    MACD = fast EMA - slow EMA
    Signal = MACD의 EMA
    Oscillator = MACD - Signal

    매수 신호: 오실레이터가 양전환(음 -> 양) 또는 상승 전환

    Args:
        weekly_data: 주봉 OHLCV 데이터 (날짜 오름차순)
        fast: 단기 EMA 기간 (기본 12)
        slow: 장기 EMA 기간 (기본 26)
        signal: 시그널 EMA 기간 (기본 9)

    Returns:
        MACDOscResult 튜플
    """
    min_required = slow + signal - 1
    if len(weekly_data) < min_required:
        return ()

    closes: list[float] = []
    for candle in weekly_data:
        if candle.close is None:
            closes.append(0.0)
        else:
            closes.append(candle.close)

    fast_ema = _ema_series(closes, fast)
    slow_ema = _ema_series(closes, slow)

    macd_values: list[float | None] = []
    for i in range(len(weekly_data)):
        f = fast_ema[i]
        s = slow_ema[i]
        if f is not None and s is not None:
            macd_values.append(f - s)
        else:
            macd_values.append(None)

    valid_macd: list[float] = []
    macd_start_idx = -1
    for i, v in enumerate(macd_values):
        if v is not None:
            if macd_start_idx < 0:
                macd_start_idx = i
            valid_macd.append(v)

    if len(valid_macd) < signal:
        return ()

    signal_ema_raw = _ema_series(valid_macd, signal)

    signal_values: list[float | None] = [None] * len(weekly_data)
    for i, val in enumerate(signal_ema_raw):
        signal_values[macd_start_idx + i] = val

    oscillator_values: list[float | None] = [None] * len(weekly_data)
    for i in range(len(weekly_data)):
        m = macd_values[i]
        s = signal_values[i]
        if m is not None and s is not None:
            oscillator_values[i] = m - s

    start_index = slow + signal - 2
    results: list[MACDOscResult] = []

    for i in range(start_index, len(weekly_data)):
        osc = oscillator_values[i]

        buy_signal = False
        if osc is not None and i > 0:
            prev_osc = oscillator_values[i - 1]
            if prev_osc is not None:
                if prev_osc <= 0 and osc > 0:
                    buy_signal = True
                elif osc > prev_osc and osc > 0:
                    buy_signal = True

        results.append(MACDOscResult(
            date=weekly_data[i].date,
            macd=macd_values[i],
            signal=signal_values[i],
            oscillator=osc,
            buy_signal=buy_signal,
        ))

    return tuple(results)
