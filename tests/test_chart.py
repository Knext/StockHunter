"""차트 생성 모듈 테스트."""

import random
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.screener.types import DreamTeamSignal
from src.types.ohlcv import OHLCV, StockData
from src.types.stock import StockInfo
from src.visualization.chart import (
    _compute_sma,
    _sanitize_filename,
    _slice_recent,
    generate_all_charts,
    generate_stock_chart,
)


def _make_stock_info() -> StockInfo:
    return StockInfo(
        code="005930",
        name="삼성전자",
        market="KOSPI",
        sector="전기전자",
    )


def _make_ohlcv_data(days: int, start_date: date | None = None) -> tuple[OHLCV, ...]:
    """테스트용 OHLCV 데이터를 생성한다."""
    if start_date is None:
        start_date = date(2024, 1, 2)

    random.seed(42)
    base_price = 70000.0
    result: list[OHLCV] = []

    for i in range(days):
        d = start_date + timedelta(days=i)
        open_price = base_price + random.uniform(-2000, 2000)
        close_price = open_price + random.uniform(-1500, 1500)
        high_price = max(open_price, close_price) + random.uniform(0, 500)
        low_price = min(open_price, close_price) - random.uniform(0, 500)
        volume = random.randint(1000000, 10000000)

        result.append(OHLCV(
            date=d,
            open=round(open_price, 0),
            high=round(high_price, 0),
            low=round(low_price, 0),
            close=round(close_price, 0),
            volume=volume,
        ))
        base_price = close_price

    return tuple(result)


def _make_weekly_data(daily: tuple[OHLCV, ...]) -> tuple[OHLCV, ...]:
    """일봉에서 간단한 주봉 데이터를 생성한다."""
    result: list[OHLCV] = []
    for i in range(0, len(daily), 5):
        chunk = daily[i:i + 5]
        if not chunk:
            continue
        opens = [c.open for c in chunk if c.open is not None]
        highs = [c.high for c in chunk if c.high is not None]
        lows = [c.low for c in chunk if c.low is not None]
        closes = [c.close for c in chunk if c.close is not None]
        volumes = [c.volume for c in chunk if c.volume is not None]

        if opens and highs and lows and closes:
            result.append(OHLCV(
                date=chunk[-1].date,
                open=opens[0],
                high=max(highs),
                low=min(lows),
                close=closes[-1],
                volume=sum(volumes) if volumes else 0,
            ))
    return tuple(result)


def _make_signal(info: StockInfo, signal_date: date) -> DreamTeamSignal:
    return DreamTeamSignal(
        stock_info=info,
        date=signal_date,
        dmi_signal=True,
        stochastic_signal=True,
        chaikin_signal=True,
        macd_signal=False,
        demark_signal=False,
        signal_strength=3,
        signal_grade="A",
    )


def _make_stock_data(days: int) -> StockData:
    info = _make_stock_info()
    daily = _make_ohlcv_data(days)
    weekly = _make_weekly_data(daily)
    return StockData(info=info, daily=daily, weekly=weekly)


class TestComputeSma:
    def test_sma_basic(self) -> None:
        closes: list[float | None] = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = _compute_sma(closes, 3)
        assert result[0] is None
        assert result[1] is None
        assert result[2] == pytest.approx(20.0)
        assert result[3] == pytest.approx(30.0)
        assert result[4] == pytest.approx(40.0)

    def test_sma_with_none(self) -> None:
        closes: list[float | None] = [10.0, None, 30.0, 40.0]
        result = _compute_sma(closes, 3)
        assert result[2] is None


class TestSanitizeFilename:
    def test_removes_special_chars(self) -> None:
        assert _sanitize_filename('삼성/전자') == '삼성전자'
        assert _sanitize_filename('LG<화학>') == 'LG화학'

    def test_normal_name_unchanged(self) -> None:
        assert _sanitize_filename('삼성전자') == '삼성전자'


class TestSliceRecent:
    def test_returns_all_when_less_than_days(self) -> None:
        data = _make_ohlcv_data(30)
        result = _slice_recent(data, 60)
        assert len(result) == 30

    def test_returns_last_n_days(self) -> None:
        data = _make_ohlcv_data(100)
        result = _slice_recent(data, 60)
        assert len(result) == 60
        assert result[0] == data[40]


class TestGenerateStockChart:
    def test_creates_png_file(self, tmp_path: Path) -> None:
        stock_data = _make_stock_data(100)
        signal = _make_signal(stock_data.info, stock_data.daily[-10].date)

        result = generate_stock_chart(stock_data, signal, tmp_path)

        assert result.exists()
        assert result.suffix == ".png"
        assert "005930" in result.name
        assert result.stat().st_size > 0

    def test_works_with_less_than_60_days(self, tmp_path: Path) -> None:
        stock_data = _make_stock_data(30)
        signal = _make_signal(stock_data.info, stock_data.daily[-1].date)

        result = generate_stock_chart(stock_data, signal, tmp_path)

        assert result.exists()
        assert result.suffix == ".png"

    def test_creates_output_directory(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "charts" / "nested"
        stock_data = _make_stock_data(80)
        signal = _make_signal(stock_data.info, stock_data.daily[-5].date)

        result = generate_stock_chart(stock_data, signal, output_dir)

        assert output_dir.exists()
        assert result.exists()


class TestGenerateAllCharts:
    def test_generates_multiple_charts(self, tmp_path: Path) -> None:
        stock_data1 = _make_stock_data(100)
        info2 = StockInfo(code="000660", name="SK하이닉스", market="KOSPI", sector="전기전자")
        daily2 = _make_ohlcv_data(100, start_date=date(2024, 3, 1))
        weekly2 = _make_weekly_data(daily2)
        stock_data2 = StockData(info=info2, daily=daily2, weekly=weekly2)

        signal1 = _make_signal(stock_data1.info, stock_data1.daily[-10].date)
        signal2 = _make_signal(info2, daily2[-10].date)

        signals = (signal1, signal2)
        data_map = {
            "005930": stock_data1,
            "000660": stock_data2,
        }

        results = generate_all_charts(signals, data_map, tmp_path)

        assert len(results) == 2
        assert "005930" in results
        assert "000660" in results
        for path in results.values():
            assert path.exists()

    def test_skips_missing_stock_data(self, tmp_path: Path) -> None:
        stock_data = _make_stock_data(100)
        signal1 = _make_signal(stock_data.info, stock_data.daily[-10].date)
        missing_info = StockInfo(code="999999", name="없는종목", market="KOSPI", sector="기타")
        signal2 = _make_signal(missing_info, date(2024, 4, 1))

        signals = (signal1, signal2)
        data_map = {"005930": stock_data}

        results = generate_all_charts(signals, data_map, tmp_path)

        assert len(results) == 1
        assert "005930" in results

    def test_skips_failed_chart(self, tmp_path: Path) -> None:
        info = _make_stock_info()
        empty_data = StockData(info=info, daily=(), weekly=())
        signal = _make_signal(info, date(2024, 1, 15))

        signals = (signal,)
        data_map = {"005930": empty_data}

        results = generate_all_charts(signals, data_map, tmp_path)

        assert isinstance(results, dict)
