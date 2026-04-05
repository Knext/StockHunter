"""캔들스틱 + 5개 지표 서브플롯 차트 생성 모듈.

matplotlib만 사용하여 종목별 기술적 분석 차트를 PNG로 생성한다.
"""

import logging
import re
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from src.indicators.chaikin import calculate_chaikin
from src.indicators.dmi import calculate_dmi
from src.indicators.macd import calculate_macd_oscillator
from src.indicators.stochastic import calculate_stochastic
from src.screener.types import DreamTeamSignal
from src.types.ohlcv import OHLCV, StockData
from src.visualization.styles import (
    CANDLE_DAYS,
    CHART_DPI,
    CHART_HEIGHT,
    CHART_WIDTH,
    COLOR_ADX,
    COLOR_BUY_MARKER,
    COLOR_CHAIKIN,
    COLOR_DOWN,
    COLOR_GRID,
    COLOR_HIST_NEG,
    COLOR_HIST_POS,
    COLOR_MA5,
    COLOR_MA20,
    COLOR_MA60,
    COLOR_MACD,
    COLOR_MINUS_DI,
    COLOR_PLUS_DI,
    COLOR_REFERENCE,
    COLOR_SIGNAL_LINE,
    COLOR_STOCH_D,
    COLOR_STOCH_K,
    COLOR_UP,
    MA_PERIODS,
    setup_korean_font,
)

logger = logging.getLogger(__name__)


def _compute_sma(
    closes: list[float | None],
    period: int,
) -> list[float | None]:
    """종가 기준 단순 이동평균을 계산한다.

    Args:
        closes: 종가 리스트
        period: 이동평균 기간

    Returns:
        SMA 값 리스트 (동일 길이, 초기값은 None)
    """
    result: list[float | None] = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(None)
            continue
        window = closes[i - period + 1:i + 1]
        if any(v is None for v in window):
            result.append(None)
            continue
        result.append(sum(v for v in window if v is not None) / period)
    return result


def _sanitize_filename(name: str) -> str:
    """파일명에서 특수문자를 제거한다."""
    return re.sub(r'[/\\:*?"<>|]', '', name)


def _slice_recent(
    data: tuple[OHLCV, ...],
    days: int,
) -> tuple[OHLCV, ...]:
    """최근 N일 데이터만 슬라이싱한다."""
    if len(data) <= days:
        return data
    return data[-days:]


def _draw_candlestick(
    ax: plt.Axes,
    data: tuple[OHLCV, ...],
    x_indices: list[int],
    signal_date: date,
) -> None:
    """캔들스틱 + 이동평균선 + 매수 신호 마커를 그린다."""
    dates = [d.date for d in data]
    closes = [d.close for d in data]
    opens = [d.open for d in data]

    for i, candle in enumerate(data):
        if candle.open is None or candle.close is None:
            continue
        if candle.high is None or candle.low is None:
            continue

        color = COLOR_UP if candle.close >= candle.open else COLOR_DOWN
        body_bottom = min(candle.open, candle.close)
        body_height = abs(candle.close - candle.open)

        if body_height == 0:
            body_height = 0.01

        ax.bar(
            x_indices[i], body_height,
            bottom=body_bottom, width=0.6,
            color=color, edgecolor=color, linewidth=0.5,
        )
        ax.vlines(
            x_indices[i], candle.low, candle.high,
            color=color, linewidth=0.8,
        )

    ma_colors = {
        MA_PERIODS[0]: COLOR_MA5,
        MA_PERIODS[1]: COLOR_MA20,
        MA_PERIODS[2]: COLOR_MA60,
    }
    for period, color in ma_colors.items():
        sma = _compute_sma(closes, period)
        valid_x = [x_indices[i] for i in range(len(sma)) if sma[i] is not None]
        valid_y = [v for v in sma if v is not None]
        if valid_x:
            ax.plot(valid_x, valid_y, color=color, linewidth=1.0,
                    label=f"MA{period}")

    for i, d in enumerate(dates):
        if d == signal_date:
            low_val = data[i].low
            if low_val is not None:
                ax.plot(
                    x_indices[i], low_val * 0.98,
                    marker="^", color=COLOR_BUY_MARKER,
                    markersize=10, zorder=10,
                )
            break

    ax.legend(loc="upper left", fontsize=7)
    ax.set_ylabel("가격")
    ax.grid(True, color=COLOR_GRID, linewidth=0.5, alpha=0.7)


def _draw_volume(
    ax: plt.Axes,
    data: tuple[OHLCV, ...],
    x_indices: list[int],
) -> None:
    """거래량 바를 그린다."""
    for i, candle in enumerate(data):
        if candle.volume is None or candle.volume == 0:
            continue
        if candle.open is None or candle.close is None:
            color = COLOR_DOWN
        else:
            color = COLOR_UP if candle.close >= candle.open else COLOR_DOWN
        ax.bar(x_indices[i], candle.volume, width=0.6, color=color, alpha=0.7)

    ax.set_ylabel("거래량")
    ax.grid(True, color=COLOR_GRID, linewidth=0.5, alpha=0.7)


def _highlight_buy_signals(
    ax: plt.Axes,
    signal_dates: list[date],
    date_to_x: dict[date, int],
) -> None:
    """매수 신호가 있는 날에 배경 하이라이트를 추가한다."""
    for d in signal_dates:
        x = date_to_x.get(d)
        if x is not None:
            ax.axvspan(x - 0.5, x + 0.5, alpha=0.1, color=COLOR_BUY_MARKER)


def _draw_dmi(
    ax: plt.Axes,
    daily_data: tuple[OHLCV, ...],
    date_to_x: dict[date, int],
) -> None:
    """DMI 서브플롯을 그린다."""
    results = calculate_dmi(daily_data)
    if not results:
        ax.set_ylabel("DMI")
        return

    x_vals = [date_to_x[r.date] for r in results if r.date in date_to_x]
    filtered = [r for r in results if r.date in date_to_x]

    plus_di_x = [date_to_x[r.date] for r in filtered if r.plus_di is not None]
    plus_di_y = [r.plus_di for r in filtered if r.plus_di is not None]
    minus_di_x = [date_to_x[r.date] for r in filtered if r.minus_di is not None]
    minus_di_y = [r.minus_di for r in filtered if r.minus_di is not None]
    adx_x = [date_to_x[r.date] for r in filtered if r.adx is not None]
    adx_y = [r.adx for r in filtered if r.adx is not None]

    if plus_di_x:
        ax.plot(plus_di_x, plus_di_y, color=COLOR_PLUS_DI, linewidth=1.0, label="+DI")
    if minus_di_x:
        ax.plot(minus_di_x, minus_di_y, color=COLOR_MINUS_DI, linewidth=1.0, label="-DI")
    if adx_x:
        ax.plot(adx_x, adx_y, color=COLOR_ADX, linewidth=1.0, label="ADX")

    if x_vals:
        ax.axhline(y=30, color=COLOR_REFERENCE, linestyle="--", linewidth=0.5)

    buy_dates = [r.date for r in filtered if r.buy_signal]
    _highlight_buy_signals(ax, buy_dates, date_to_x)

    ax.legend(loc="upper left", fontsize=7)
    ax.set_ylabel("DMI")
    ax.grid(True, color=COLOR_GRID, linewidth=0.5, alpha=0.7)


def _draw_stochastic(
    ax: plt.Axes,
    daily_data: tuple[OHLCV, ...],
    date_to_x: dict[date, int],
) -> None:
    """스토캐스틱 서브플롯을 그린다."""
    results = calculate_stochastic(daily_data)
    if not results:
        ax.set_ylabel("Stochastic")
        return

    filtered = [r for r in results if r.date in date_to_x]

    k_x = [date_to_x[r.date] for r in filtered if r.k is not None]
    k_y = [r.k for r in filtered if r.k is not None]
    d_x = [date_to_x[r.date] for r in filtered if r.d is not None]
    d_y = [r.d for r in filtered if r.d is not None]

    if k_x:
        ax.plot(k_x, k_y, color=COLOR_STOCH_K, linewidth=1.0, label="%K")
    if d_x:
        ax.plot(d_x, d_y, color=COLOR_STOCH_D, linewidth=1.0, label="%D")

    x_vals = [date_to_x[r.date] for r in filtered]
    if x_vals:
        ax.axhline(y=80, color=COLOR_REFERENCE, linestyle="--", linewidth=0.5)
        ax.axhline(y=20, color=COLOR_REFERENCE, linestyle="--", linewidth=0.5)

    buy_dates = [r.date for r in filtered if r.buy_reinforcement]
    _highlight_buy_signals(ax, buy_dates, date_to_x)

    ax.legend(loc="upper left", fontsize=7)
    ax.set_ylabel("Stochastic")
    ax.grid(True, color=COLOR_GRID, linewidth=0.5, alpha=0.7)


def _draw_chaikin(
    ax: plt.Axes,
    daily_data: tuple[OHLCV, ...],
    date_to_x: dict[date, int],
) -> None:
    """채킨 오실레이터 서브플롯을 그린다."""
    results = calculate_chaikin(daily_data)
    if not results:
        ax.set_ylabel("Chaikin")
        return

    filtered = [r for r in results if r.date in date_to_x]

    co_x = [date_to_x[r.date] for r in filtered if r.co_value is not None]
    co_y = [r.co_value for r in filtered if r.co_value is not None]

    if co_x:
        ax.plot(co_x, co_y, color=COLOR_CHAIKIN, linewidth=1.0, label="CO")

    x_vals = [date_to_x[r.date] for r in filtered]
    if x_vals:
        ax.axhline(y=0, color=COLOR_REFERENCE, linestyle="--", linewidth=0.5)

    buy_dates = [r.date for r in filtered if r.buy_signal]
    _highlight_buy_signals(ax, buy_dates, date_to_x)

    ax.legend(loc="upper left", fontsize=7)
    ax.set_ylabel("Chaikin")
    ax.grid(True, color=COLOR_GRID, linewidth=0.5, alpha=0.7)


def _snap_weekly_to_daily(
    weekly_date: date,
    daily_dates: list[date],
) -> int | None:
    """주봉 날짜를 가장 가까운 일봉 x좌표로 매핑한다.

    주봉의 날짜(해당 주 마지막 거래일)가 슬라이싱된 일봉 범위에
    정확히 없을 수 있으므로, 가장 가까운 이전 일봉 날짜를 찾는다.
    """
    best_idx = None
    for i, d in enumerate(daily_dates):
        if d <= weekly_date:
            best_idx = i
    return best_idx


def _draw_macd(
    ax: plt.Axes,
    weekly_data: tuple[OHLCV, ...],
    date_to_x: dict[date, int],
) -> None:
    """MACD 서브플롯을 그린다."""
    results = calculate_macd_oscillator(weekly_data)
    if not results:
        ax.set_ylabel("MACD")
        return

    daily_dates = sorted(date_to_x.keys())
    if not daily_dates:
        ax.set_ylabel("MACD")
        return

    min_date = daily_dates[0]
    max_date = daily_dates[-1]

    mapped: list[tuple[int, object]] = []
    for r in results:
        if r.date < min_date:
            continue
        if r.date > max_date:
            continue
        x = date_to_x.get(r.date)
        if x is None:
            x = _snap_weekly_to_daily(r.date, daily_dates)
        if x is not None:
            mapped.append((x, r))

    for x, r in mapped:
        if r.oscillator is not None:
            color = COLOR_HIST_POS if r.oscillator >= 0 else COLOR_HIST_NEG
            ax.bar(x, r.oscillator, width=2.5, color=color, alpha=0.7)

    macd_x = [x for x, r in mapped if r.macd is not None]
    macd_y = [r.macd for _, r in mapped if r.macd is not None]
    signal_x = [x for x, r in mapped if r.signal is not None]
    signal_y = [r.signal for _, r in mapped if r.signal is not None]

    if macd_x:
        ax.plot(macd_x, macd_y, color=COLOR_MACD, linewidth=1.0, label="MACD")
    if signal_x:
        ax.plot(signal_x, signal_y, color=COLOR_SIGNAL_LINE, linewidth=1.0, label="Signal")

    buy_dates = [r.date for _, r in mapped if r.buy_signal]
    _highlight_buy_signals(ax, buy_dates, date_to_x)

    ax.legend(loc="upper left", fontsize=7)
    ax.set_ylabel("MACD (주봉)")
    ax.grid(True, color=COLOR_GRID, linewidth=0.5, alpha=0.7)


def _draw_signal_badge(
    ax: plt.Axes,
    active: bool,
    label: str,
) -> None:
    """서브플롯 우상단에 매수 신호 배지를 그린다."""
    if active:
        text = f"  {label}  "
        ax.text(
            0.99, 0.95, text,
            transform=ax.transAxes,
            ha="right", va="top",
            fontsize=8, fontweight="bold",
            color="#fff",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#D32F2F",
                edgecolor="#B71C1C",
                alpha=0.95,
            ),
            zorder=100,
        )
    else:
        text = f"  {label}  "
        ax.text(
            0.99, 0.95, text,
            transform=ax.transAxes,
            ha="right", va="top",
            fontsize=8,
            color="#bbb",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#f0f0f0",
                edgecolor="#ddd",
                alpha=0.7,
            ),
            zorder=100,
        )


def _format_x_axis(
    axes: list[plt.Axes],
    data: tuple[OHLCV, ...],
    x_indices: list[int],
) -> None:
    """모든 서브플롯의 x축 날짜를 포맷한다."""
    dates = [d.date for d in data]
    total = len(dates)

    if total <= 15:
        step = 1
    elif total <= 30:
        step = 5
    else:
        step = 10

    tick_positions = list(range(0, total, step))
    tick_labels = [dates[i].strftime("%m/%d") for i in tick_positions]

    for ax in axes:
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, fontsize=7)


def generate_stock_chart(
    stock_data: StockData,
    signal: DreamTeamSignal,
    output_dir: Path,
) -> Path:
    """단일 종목 차트를 PNG로 생성 및 저장한다.

    Args:
        stock_data: 종목 OHLCV 데이터
        signal: 드림팀 매수 신호
        output_dir: 출력 디렉토리

    Returns:
        생성된 PNG 파일 경로
    """
    setup_korean_font()

    daily_sliced = _slice_recent(stock_data.daily, CANDLE_DAYS)
    x_indices = list(range(len(daily_sliced)))
    date_to_x: dict[date, int] = {
        d.date: i for i, d in enumerate(daily_sliced)
    }

    fig = plt.figure(figsize=(CHART_WIDTH, CHART_HEIGHT))
    gs = GridSpec(
        6, 1, figure=fig,
        height_ratios=[4, 1, 1.5, 1.5, 1.5, 1.5],
        hspace=0.3,
    )

    ax_candle = fig.add_subplot(gs[0])
    ax_volume = fig.add_subplot(gs[1], sharex=ax_candle)
    ax_dmi = fig.add_subplot(gs[2], sharex=ax_candle)
    ax_stoch = fig.add_subplot(gs[3], sharex=ax_candle)
    ax_chaikin = fig.add_subplot(gs[4], sharex=ax_candle)
    ax_macd = fig.add_subplot(gs[5], sharex=ax_candle)

    all_axes = [ax_candle, ax_volume, ax_dmi, ax_stoch, ax_chaikin, ax_macd]

    title = f"{stock_data.info.name} ({stock_data.info.code}) \u2014 {signal.signal_grade}"
    ax_candle.set_title(title, fontsize=14, fontweight="bold")

    _draw_candlestick(ax_candle, daily_sliced, x_indices, signal.date)
    _draw_volume(ax_volume, daily_sliced, x_indices)
    _draw_dmi(ax_dmi, stock_data.daily, date_to_x)
    _draw_stochastic(ax_stoch, stock_data.daily, date_to_x)
    _draw_chaikin(ax_chaikin, stock_data.daily, date_to_x)
    _draw_macd(ax_macd, stock_data.weekly, date_to_x)

    _draw_signal_badge(ax_candle, signal.demark_signal, "드마크 완성")
    _draw_signal_badge(ax_dmi, signal.dmi_signal, "DMI 매수")
    _draw_signal_badge(ax_stoch, signal.stochastic_signal, "스토캐스틱 강화")
    _draw_signal_badge(ax_chaikin, signal.chaikin_signal, "채킨 돌파")
    _draw_signal_badge(ax_macd, signal.macd_signal, "MACD 호전")

    _format_x_axis(all_axes, daily_sliced, x_indices)

    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_filename(stock_data.info.name)
    filename = f"{stock_data.info.code}_{safe_name}.png"
    output_path = output_dir / filename

    try:
        fig.savefig(
            output_path,
            dpi=CHART_DPI,
            bbox_inches="tight",
            facecolor="white",
        )
        logger.info("차트 생성 완료: %s", output_path)
    finally:
        plt.close(fig)

    return output_path


def generate_all_charts(
    signals: tuple[DreamTeamSignal, ...],
    stock_data_map: dict[str, StockData],
    output_dir: Path,
) -> dict[str, Path]:
    """전체 종목 차트를 일괄 생성한다.

    개별 차트 생성 실패 시 해당 종목을 스킵하고 나머지를 계속 생성한다.

    Args:
        signals: 드림팀 매수 신호 튜플
        stock_data_map: 종목코드 -> StockData 매핑
        output_dir: 출력 디렉토리

    Returns:
        종목코드 -> PNG 파일 경로 딕셔너리
    """
    results: dict[str, Path] = {}

    for signal in signals:
        code = signal.stock_info.code
        stock_data = stock_data_map.get(code)

        if stock_data is None:
            logger.warning("종목 데이터 없음: %s (%s)", code, signal.stock_info.name)
            continue

        try:
            path = generate_stock_chart(stock_data, signal, output_dir)
            results[code] = path
        except Exception:
            logger.exception(
                "차트 생성 실패: %s (%s)", code, signal.stock_info.name,
            )

    logger.info("차트 생성 완료: %d/%d", len(results), len(signals))
    return results


def generate_index_chart(
    stock_data: StockData,
    output_dir: Path,
) -> Path:
    """시장 지수 차트를 PNG로 생성한다.

    종목 차트와 동일한 구조: 캔들스틱 + 거래량 + DMI + 스토캐스틱 + 채킨 + MACD.

    Args:
        stock_data: 지수 OHLCV 데이터
        output_dir: 출력 디렉토리

    Returns:
        생성된 PNG 파일 경로
    """
    setup_korean_font()

    daily_sliced = _slice_recent(stock_data.daily, CANDLE_DAYS)
    if not daily_sliced:
        raise ValueError(f"지수 데이터 없음: {stock_data.info.code}")

    x_indices = list(range(len(daily_sliced)))
    date_to_x: dict[date, int] = {
        d.date: i for i, d in enumerate(daily_sliced)
    }

    fig = plt.figure(figsize=(CHART_WIDTH, CHART_HEIGHT))
    gs = GridSpec(
        6, 1, figure=fig,
        height_ratios=[4, 1, 1.5, 1.5, 1.5, 1.5],
        hspace=0.3,
    )

    ax_candle = fig.add_subplot(gs[0])
    ax_volume = fig.add_subplot(gs[1], sharex=ax_candle)
    ax_dmi = fig.add_subplot(gs[2], sharex=ax_candle)
    ax_stoch = fig.add_subplot(gs[3], sharex=ax_candle)
    ax_chaikin = fig.add_subplot(gs[4], sharex=ax_candle)
    ax_macd = fig.add_subplot(gs[5], sharex=ax_candle)

    all_axes = [ax_candle, ax_volume, ax_dmi, ax_stoch, ax_chaikin, ax_macd]

    title = f"{stock_data.info.name} 지수"
    ax_candle.set_title(title, fontsize=14, fontweight="bold")

    _draw_candlestick(
        ax_candle, daily_sliced, x_indices,
        signal_date=date(1900, 1, 1),
    )
    _draw_volume(ax_volume, daily_sliced, x_indices)
    _draw_dmi(ax_dmi, stock_data.daily, date_to_x)
    _draw_stochastic(ax_stoch, stock_data.daily, date_to_x)
    _draw_chaikin(ax_chaikin, stock_data.daily, date_to_x)
    _draw_macd(ax_macd, stock_data.weekly, date_to_x)

    _format_x_axis(all_axes, daily_sliced, x_indices)

    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_filename(stock_data.info.name)
    filename = f"index_{stock_data.info.code}_{safe_name}.png"
    output_path = output_dir / filename

    try:
        fig.savefig(
            output_path,
            dpi=CHART_DPI,
            bbox_inches="tight",
            facecolor="white",
        )
        logger.info("지수 차트 생성 완료: %s", output_path)
    finally:
        plt.close(fig)

    return output_path
