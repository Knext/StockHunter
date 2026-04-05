"""DMI (Directional Movement Index) 계산 모듈.

박문환 드림팀의 첫 번째 지표 - "저점 족집게".
J. Welles Wilder (1978) 개발.

매수 신호: -DI가 ADX를 30 이상에서 하향 돌파 + 3영업일 내 ADX 하락 전환.
"""

from src.indicators.types import DMIResult
from src.types.ohlcv import OHLCV


def _true_range(
    current: OHLCV,
    previous: OHLCV,
) -> float | None:
    """True Range 계산."""
    if (
        current.high is None
        or current.low is None
        or previous.close is None
    ):
        return None
    return max(
        current.high - current.low,
        abs(current.high - previous.close),
        abs(current.low - previous.close),
    )


def _directional_movement(
    current: OHLCV,
    previous: OHLCV,
) -> tuple[float | None, float | None]:
    """+DM, -DM 계산.

    Returns:
        (+DM, -DM) 튜플
    """
    if (
        current.high is None
        or current.low is None
        or previous.high is None
        or previous.low is None
    ):
        return None, None

    up_move = current.high - previous.high
    down_move = previous.low - current.low

    plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
    minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0

    return plus_dm, minus_dm


def calculate_dmi(
    data: tuple[OHLCV, ...],
    period: int = 14,
) -> tuple[DMIResult, ...]:
    """DMI 지표를 계산한다.

    Wilder 스무딩 방식:
        smoothed = prev_smoothed * (period-1)/period + current_value

    Args:
        data: OHLCV 데이터 (날짜 오름차순)
        period: 계산 기간 (기본 14일)

    Returns:
        DMIResult 튜플 (데이터 부족 시 빈 튜플)
    """
    if len(data) < period + 1:
        return ()

    tr_list: list[float] = []
    plus_dm_list: list[float] = []
    minus_dm_list: list[float] = []

    for i in range(1, len(data)):
        tr = _true_range(data[i], data[i - 1])
        plus_dm, minus_dm = _directional_movement(data[i], data[i - 1])

        if tr is None or plus_dm is None or minus_dm is None:
            tr_list.append(0.0)
            plus_dm_list.append(0.0)
            minus_dm_list.append(0.0)
        else:
            tr_list.append(tr)
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)

    smoothed_tr = sum(tr_list[:period])
    smoothed_plus_dm = sum(plus_dm_list[:period])
    smoothed_minus_dm = sum(minus_dm_list[:period])

    results: list[DMIResult] = []
    dx_values: list[float] = []

    adx: float | None = None

    for i in range(period - 1, len(tr_list)):
        if i == period - 1:
            pass
        else:
            smoothed_tr = (
                smoothed_tr * (period - 1) / period + tr_list[i]
            )
            smoothed_plus_dm = (
                smoothed_plus_dm * (period - 1) / period + plus_dm_list[i]
            )
            smoothed_minus_dm = (
                smoothed_minus_dm * (period - 1) / period + minus_dm_list[i]
            )

        if smoothed_tr == 0:
            plus_di = None
            minus_di = None
            dx = None
        else:
            plus_di = 100.0 * smoothed_plus_dm / smoothed_tr
            minus_di = 100.0 * smoothed_minus_dm / smoothed_tr

            di_sum = plus_di + minus_di
            if di_sum == 0:
                dx = None
            else:
                dx = 100.0 * abs(plus_di - minus_di) / di_sum

        if dx is not None:
            dx_values.append(dx)

        if adx is None:
            if len(dx_values) >= period:
                adx = sum(dx_values[:period]) / period
        else:
            if dx is not None:
                adx = (adx * (period - 1) + dx) / period

        data_index = i + 1
        results.append(DMIResult(
            date=data[data_index].date,
            plus_di=plus_di,
            minus_di=minus_di,
            adx=adx,
            buy_signal=False,
        ))

    results = _apply_buy_signals(results)

    return tuple(results)


def _apply_buy_signals(
    results: list[DMIResult],
) -> list[DMIResult]:
    """매수 신호를 적용한다.

    조건:
    1. -DI가 ADX를 30 이상에서 하향 돌파
       (이전에 -DI >= ADX였는데, 현재 -DI < ADX이고, ADX >= 30)
    2. 돌파 시점으로부터 3영업일 내 ADX가 하락 전환
    """
    crossover_indices: list[int] = []

    for i in range(1, len(results)):
        prev = results[i - 1]
        curr = results[i]

        if (
            prev.minus_di is not None
            and prev.adx is not None
            and curr.minus_di is not None
            and curr.adx is not None
            and prev.minus_di >= prev.adx
            and curr.minus_di < curr.adx
            and curr.adx >= 30
        ):
            crossover_indices.append(i)

    signal_indices: set[int] = set()

    for cross_idx in crossover_indices:
        cross_adx = results[cross_idx].adx
        if cross_adx is None:
            continue

        for offset in range(1, 4):
            check_idx = cross_idx + offset
            if check_idx >= len(results):
                break

            check_adx = results[check_idx].adx
            if check_adx is None:
                continue

            prev_adx = results[check_idx - 1].adx
            if prev_adx is not None and check_adx < prev_adx:
                signal_indices.add(cross_idx)
                break

    updated: list[DMIResult] = []
    for i, r in enumerate(results):
        if i in signal_indices:
            updated.append(DMIResult(
                date=r.date,
                plus_di=r.plus_di,
                minus_di=r.minus_di,
                adx=r.adx,
                buy_signal=True,
            ))
        else:
            updated.append(r)

    return updated
