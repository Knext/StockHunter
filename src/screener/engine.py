"""드림팀 복합 스크리닝 엔진.

드림팀 지표의 순차적 4단계 복합 조건으로 매수 신호를 판단한다.
이전 단계가 충족되어야 다음 단계로 진입할 수 있으며,
각 단계가 차례대로 충족되어야 해당 등급이 부여된다.

순차적 파이프라인 (AND, 순서 고정):
- 1단계: DMI 매수 신호 → "기본매수"
- 2단계: 1단계 + 스토캐스틱 매수 강화 → "매수강화"
- 3단계: 2단계 + 채킨 오실레이터 매수 → "이중매수"
- 4단계: 3단계 + MACD 오실레이터 주봉 매수 → "완전매수"

드마크는 보완 지표로 별도 기록되며 순차 단계에는 포함되지 않는다.
signal_strength는 도달한 순차 단계 번호(0-4)를 의미한다.

모든 파라미터는 DreamIndexConfig(dream-index-config.yaml)에서 로드된다.
"""

from src.indicators.chaikin import calculate_chaikin
from src.indicators.demark import calculate_demark
from src.indicators.dmi import calculate_dmi
from src.indicators.macd import calculate_macd_oscillator
from src.indicators.stochastic import calculate_stochastic
from src.screener.dream_config import DreamIndexConfig, load_dream_index_config
from src.screener.types import DreamTeamSignal
from src.types.ohlcv import StockData

MAX_STAGE = 4


def _determine_grade(stage: int) -> str:
    """순차 단계 번호에 따른 등급 결정."""
    if stage <= 0:
        return ""
    if stage == 1:
        return "기본매수"
    if stage == 2:
        return "매수강화"
    if stage == 3:
        return "이중매수"
    return "완전매수"


def _sequential_stage(
    dmi: bool,
    stoch: bool,
    chaikin: bool,
    macd: bool,
) -> int:
    """드림팀 지표 순서에 따른 도달 단계를 계산한다.

    앞 단계가 거짓이면 그 이후 단계는 충족되어도 카운트하지 않는다.
    """
    if not dmi:
        return 0
    if not stoch:
        return 1
    if not chaikin:
        return 2
    if not macd:
        return 3
    return 4


def screen_stock(
    stock_data: StockData,
    config: DreamIndexConfig | None = None,
) -> DreamTeamSignal | None:
    """단일 종목을 드림팀 기준으로 스크리닝한다.

    일봉: DMI, 스토캐스틱, 채킨, 드마크
    주봉: MACD 오실레이터

    가장 최근 영업일 기준으로 각 지표의 신호를 확인한다.

    Args:
        stock_data: 종목 데이터 (일봉 + 주봉)
        config: 드림팀 지표 설정. None이면 dream-index-config.yaml을 로드한다.

    Returns:
        DreamTeamSignal 또는 None (신호 없음 = 1단계 미달)
    """
    if config is None:
        config = load_dream_index_config()

    daily = stock_data.daily
    weekly = stock_data.weekly

    if not daily:
        return None

    dmi_results = calculate_dmi(daily, config.dmi.period)
    stoch_results = calculate_stochastic(
        daily,
        config.stochastic.k,
        config.stochastic.d,
        config.stochastic.slowing,
    )
    chaikin_results = calculate_chaikin(
        daily,
        config.chaikin.fast,
        config.chaikin.slow,
    )
    macd_results = calculate_macd_oscillator(
        weekly,
        config.macd.fast,
        config.macd.slow,
        config.macd.signal,
    )
    demark_results = calculate_demark(daily, config.demark.lookback)

    target_date = daily[-1].date

    dmi_signal = _has_recent_buy(
        dmi_results, config.dmi.lookback_days, lambda r: r.buy_signal,
    )
    stoch_signal = _has_recent_buy(
        stoch_results,
        config.stochastic.lookback_days,
        lambda r: r.buy_reinforcement,
    )
    chaikin_signal = _has_recent_buy(
        chaikin_results, config.chaikin.lookback_days, lambda r: r.buy_signal,
    )
    macd_signal_flag = _has_latest_macd_buy(macd_results)
    demark_signal = _has_recent_buy(
        demark_results,
        config.demark.lookback_days,
        lambda r: r.setup_complete or r.countdown_complete,
    )

    stage = _sequential_stage(
        dmi_signal,
        stoch_signal,
        chaikin_signal,
        macd_signal_flag,
    )

    if stage == 0:
        return None

    grade = _determine_grade(stage)

    return DreamTeamSignal(
        stock_info=stock_data.info,
        date=target_date,
        dmi_signal=dmi_signal,
        stochastic_signal=stoch_signal,
        chaikin_signal=chaikin_signal,
        macd_signal=macd_signal_flag,
        demark_signal=demark_signal,
        signal_strength=stage,
        signal_grade=grade,
    )


def _has_recent_buy(results: tuple, lookback_days: int, predicate) -> bool:
    """최근 N일 이내 predicate를 만족하는 결과가 있는지 확인."""
    if not results or lookback_days <= 0:
        return False
    for r in reversed(results[-lookback_days:]):
        if predicate(r):
            return True
    return False


def _has_latest_macd_buy(results: tuple) -> bool:
    """가장 최근 주봉에서 MACD 매수 신호가 있는지 확인."""
    if not results:
        return False
    return results[-1].buy_signal


def screen_all(
    stocks: list[StockData],
    config: DreamIndexConfig | None = None,
) -> list[DreamTeamSignal]:
    """전 종목을 드림팀 기준으로 스크리닝한다.

    Args:
        stocks: 종목 데이터 리스트
        config: 드림팀 지표 설정. None이면 dream-index-config.yaml을 로드한다.

    Returns:
        DreamTeamSignal 리스트 (signal_strength 내림차순 정렬)
    """
    if config is None:
        config = load_dream_index_config()

    results: list[DreamTeamSignal] = []

    for stock_data in stocks:
        try:
            signal = screen_stock(stock_data, config=config)
            if signal is not None:
                results.append(signal)
        except Exception:
            continue

    return sorted(results, key=lambda s: s.signal_strength, reverse=True)
