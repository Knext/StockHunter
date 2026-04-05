"""드림팀 복합 스크리닝 엔진.

5개 지표를 종합하여 매수 신호를 판단한다.

신호 등급:
- signal_strength 1 (DMI만): "기본매수"
- signal_strength 2 (DMI + 스토캐스틱): "매수강화"
- signal_strength 3-4: "이중매수"
- signal_strength 5: "완전매수"
"""

from src.indicators.chaikin import calculate_chaikin
from src.indicators.demark import calculate_demark
from src.indicators.dmi import calculate_dmi
from src.indicators.macd import calculate_macd_oscillator
from src.indicators.stochastic import calculate_stochastic
from src.screener.types import DreamTeamSignal
from src.types.ohlcv import StockData


def _determine_grade(strength: int) -> str:
    """신호 강도에 따른 등급 결정."""
    if strength <= 0:
        return ""
    if strength == 1:
        return "기본매수"
    if strength == 2:
        return "매수강화"
    if strength <= 4:
        return "이중매수"
    return "완전매수"


def screen_stock(
    stock_data: StockData,
    dmi_period: int = 14,
    stoch_k: int = 14,
    stoch_d: int = 3,
    stoch_slowing: int = 3,
    chaikin_fast: int = 3,
    chaikin_slow: int = 10,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    demark_lookback: int = 4,
) -> DreamTeamSignal | None:
    """단일 종목을 드림팀 기준으로 스크리닝한다.

    일봉: DMI, 스토캐스틱, 채킨, 드마크
    주봉: MACD 오실레이터

    가장 최근 영업일 기준으로 각 지표의 신호를 확인한다.

    Args:
        stock_data: 종목 데이터 (일봉 + 주봉)
        기타: 각 지표 파라미터

    Returns:
        DreamTeamSignal 또는 None (신호 없음)
    """
    daily = stock_data.daily
    weekly = stock_data.weekly

    if not daily:
        return None

    dmi_results = calculate_dmi(daily, dmi_period)
    stoch_results = calculate_stochastic(daily, stoch_k, stoch_d, stoch_slowing)
    chaikin_results = calculate_chaikin(daily, chaikin_fast, chaikin_slow)
    macd_results = calculate_macd_oscillator(weekly, macd_fast, macd_slow, macd_signal)
    demark_results = calculate_demark(daily, demark_lookback)

    target_date = daily[-1].date

    dmi_signal = _has_recent_signal_dmi(dmi_results, target_date)
    stoch_signal = _has_recent_signal_stoch(stoch_results, target_date)
    chaikin_signal = _has_recent_signal_chaikin(chaikin_results, target_date)
    macd_signal_flag = _has_recent_signal_macd(macd_results)
    demark_signal = _has_recent_signal_demark(demark_results, target_date)

    signals = [
        dmi_signal,
        stoch_signal,
        chaikin_signal,
        macd_signal_flag,
        demark_signal,
    ]
    strength = sum(1 for s in signals if s)

    if strength == 0:
        return None

    grade = _determine_grade(strength)

    return DreamTeamSignal(
        stock_info=stock_data.info,
        date=target_date,
        dmi_signal=dmi_signal,
        stochastic_signal=stoch_signal,
        chaikin_signal=chaikin_signal,
        macd_signal=macd_signal_flag,
        demark_signal=demark_signal,
        signal_strength=strength,
        signal_grade=grade,
    )


def _has_recent_signal_dmi(
    results: tuple,
    target_date,
    lookback_days: int = 5,
) -> bool:
    """최근 N일 이내 DMI 매수 신호가 있는지 확인."""
    if not results:
        return False

    for r in reversed(results[-lookback_days:]):
        if r.buy_signal:
            return True
    return False


def _has_recent_signal_stoch(
    results: tuple,
    target_date,
    lookback_days: int = 5,
) -> bool:
    """최근 N일 이내 스토캐스틱 매수 강화가 있는지 확인."""
    if not results:
        return False

    for r in reversed(results[-lookback_days:]):
        if r.buy_reinforcement:
            return True
    return False


def _has_recent_signal_chaikin(
    results: tuple,
    target_date,
    lookback_days: int = 5,
) -> bool:
    """최근 N일 이내 채킨 매수 신호가 있는지 확인."""
    if not results:
        return False

    for r in reversed(results[-lookback_days:]):
        if r.buy_signal:
            return True
    return False


def _has_recent_signal_macd(
    results: tuple,
) -> bool:
    """가장 최근 주봉에서 MACD 매수 신호가 있는지 확인."""
    if not results:
        return False

    return results[-1].buy_signal


def _has_recent_signal_demark(
    results: tuple,
    target_date,
    lookback_days: int = 5,
) -> bool:
    """최근 N일 이내 드마크 신호가 있는지 확인."""
    if not results:
        return False

    for r in reversed(results[-lookback_days:]):
        if r.setup_complete or r.countdown_complete:
            return True
    return False


def screen_all(
    stocks: list[StockData],
    **kwargs,
) -> list[DreamTeamSignal]:
    """전 종목을 드림팀 기준으로 스크리닝한다.

    Args:
        stocks: 종목 데이터 리스트
        **kwargs: screen_stock에 전달할 파라미터

    Returns:
        DreamTeamSignal 리스트 (signal_strength 내림차순 정렬)
    """
    results: list[DreamTeamSignal] = []

    for stock_data in stocks:
        try:
            signal = screen_stock(stock_data, **kwargs)
            if signal is not None:
                results.append(signal)
        except Exception:
            continue

    return sorted(results, key=lambda s: s.signal_strength, reverse=True)
