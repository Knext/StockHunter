"""드마크 (DeMark / TD Sequential) 계산 모듈.

박문환 드림팀의 보완 지표.
Tom DeMark 개발.

TD Sequential: Setup 9 + Countdown 13.
4봉 비교 기반 연속 카운팅.
"""

from src.indicators.types import DeMarkResult
from src.types.ohlcv import OHLCV


def calculate_demark(
    data: tuple[OHLCV, ...],
    lookback: int = 4,
) -> tuple[DeMarkResult, ...]:
    """TD Sequential을 계산한다.

    TD Buy Setup: 현재 종가가 lookback봉 전 종가보다 낮으면 카운트 증가.
                  연속 9회 달성 시 setup_complete = True.

    TD Buy Countdown: Setup 완성 후, 현재 종가가 2봉 전 저가보다
                      낮거나 같으면 카운트 증가.
                      13회 달성 시 countdown_complete = True.

    Args:
        data: OHLCV 데이터 (날짜 오름차순)
        lookback: 비교 봉 수 (기본 4)

    Returns:
        DeMarkResult 튜플
    """
    if len(data) < lookback + 1:
        return ()

    results: list[DeMarkResult] = []
    setup_count = 0
    countdown_count = 0
    in_countdown = False
    setup_direction: str | None = None

    for i in range(lookback, len(data)):
        current_close = data[i].close
        compare_close = data[i - lookback].close

        if current_close is None or compare_close is None:
            results.append(DeMarkResult(
                date=data[i].date,
                setup_count=0,
                countdown_count=countdown_count if in_countdown else 0,
                setup_complete=False,
                countdown_complete=False,
            ))
            setup_count = 0
            if not in_countdown:
                countdown_count = 0
            continue

        is_buy_setup = current_close < compare_close
        is_sell_setup = current_close > compare_close

        setup_complete = False

        if is_buy_setup:
            if setup_direction == "buy":
                setup_count += 1
            else:
                setup_count = 1
                setup_direction = "buy"
        elif is_sell_setup:
            if setup_direction == "sell":
                setup_count += 1
            else:
                setup_count = 1
                setup_direction = "sell"
        else:
            setup_count = 0
            setup_direction = None

        if setup_count >= 9:
            setup_complete = True
            in_countdown = True
            countdown_count = 0
            setup_count = 9

        countdown_complete = False
        if in_countdown and i >= 2:
            current_close_val = data[i].close
            compare_low = data[i - 2].low

            if (
                current_close_val is not None
                and compare_low is not None
                and current_close_val <= compare_low
            ):
                countdown_count += 1

            if countdown_count >= 13:
                countdown_complete = True
                in_countdown = False
                countdown_count = 13

        results.append(DeMarkResult(
            date=data[i].date,
            setup_count=min(setup_count, 9),
            countdown_count=min(countdown_count, 13),
            setup_complete=setup_complete,
            countdown_complete=countdown_complete,
        ))

        if countdown_complete:
            countdown_count = 0

    return tuple(results)
