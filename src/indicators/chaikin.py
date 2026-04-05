"""채킨 오실레이터 (Chaikin's Oscillator) 계산 모듈.

박문환 드림팀의 세 번째 지표 - "수급 확인".
Marc Chaikin 개발.

CO = ADL의 단기 EMA(3일) - ADL의 장기 EMA(10일)
매수: 0선 상향 돌파 (매집 우위).
"""

from src.indicators.types import ChaikinResult
from src.types.ohlcv import OHLCV


def _money_flow_multiplier(candle: OHLCV) -> float | None:
    """Money Flow Multiplier 계산.

    MFM = ((Close - Low) - (High - Close)) / (High - Low)
    """
    if candle.close is None or candle.high is None or candle.low is None:
        return None

    high_low = candle.high - candle.low
    if high_low == 0:
        return None

    return ((candle.close - candle.low) - (candle.high - candle.close)) / high_low


def _money_flow_volume(candle: OHLCV) -> float | None:
    """Money Flow Volume 계산.

    MFV = MFM * Volume
    """
    mfm = _money_flow_multiplier(candle)
    if mfm is None or candle.volume is None:
        return None

    return mfm * candle.volume


def _ema(
    values: list[float],
    period: int,
) -> list[float]:
    """EMA 계산.

    Args:
        values: 입력 값 리스트
        period: EMA 기간

    Returns:
        EMA 값 리스트 (입력과 동일 길이)
    """
    if len(values) < period:
        return []

    multiplier = 2.0 / (period + 1)

    sma = sum(values[:period]) / period
    result = [0.0] * (period - 1) + [sma]

    for i in range(period, len(values)):
        ema_val = (values[i] - result[-1]) * multiplier + result[-1]
        result.append(ema_val)

    return result


def calculate_chaikin(
    data: tuple[OHLCV, ...],
    fast_period: int = 3,
    slow_period: int = 10,
) -> tuple[ChaikinResult, ...]:
    """채킨 오실레이터를 계산한다.

    1. ADL(Accumulation/Distribution Line) 계산
    2. ADL의 단기 EMA - 장기 EMA

    Args:
        data: OHLCV 데이터 (날짜 오름차순)
        fast_period: 단기 EMA 기간 (기본 3)
        slow_period: 장기 EMA 기간 (기본 10)

    Returns:
        ChaikinResult 튜플
    """
    if len(data) < slow_period:
        return ()

    adl_values: list[float] = []
    valid_indices: list[int] = []
    cumulative_adl = 0.0

    for i in range(len(data)):
        mfv = _money_flow_volume(data[i])
        if mfv is None:
            adl_values.append(cumulative_adl)
        else:
            cumulative_adl += mfv
            adl_values.append(cumulative_adl)
        valid_indices.append(i)

    fast_ema = _ema(adl_values, fast_period)
    slow_ema = _ema(adl_values, slow_period)

    if not fast_ema or not slow_ema:
        return ()

    results: list[ChaikinResult] = []
    start_index = slow_period - 1

    for i in range(start_index, len(data)):
        if i < len(fast_ema) and i < len(slow_ema):
            co_value = fast_ema[i] - slow_ema[i]

            buy_signal = False
            if i > start_index and (i - 1) < len(fast_ema) and (i - 1) < len(slow_ema):
                prev_co = fast_ema[i - 1] - slow_ema[i - 1]
                if prev_co <= 0 and co_value > 0:
                    buy_signal = True

            results.append(ChaikinResult(
                date=data[i].date,
                co_value=co_value,
                buy_signal=buy_signal,
            ))

    return tuple(results)
