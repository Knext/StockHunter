"""드림팀 스크리닝 엔진 단위 테스트."""

from datetime import date, timedelta

import pytest

from src.screener.dream_config import (
    DMIConfig,
    DreamIndexConfig,
    StochasticConfig,
)
from src.screener.engine import screen_all, screen_stock, _determine_grade
from src.screener.types import DreamTeamSignal
from src.types.ohlcv import OHLCV, StockData
from src.types.stock import StockInfo


def _make_ohlcv(
    day_offset: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int = 10000,
    base_date: date = date(2024, 1, 1),
) -> OHLCV:
    return OHLCV(
        date=base_date + timedelta(days=day_offset),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _make_daily_data(count: int, step: float = 1.0) -> tuple[OHLCV, ...]:
    data = []
    price = 100.0
    for i in range(count):
        price += step
        data.append(_make_ohlcv(
            i, price - 0.5, price + 2.0, price - 2.0, price,
        ))
    return tuple(data)


def _make_weekly_data(count: int, step: float = 2.0) -> tuple[OHLCV, ...]:
    data = []
    price = 100.0
    for i in range(count):
        price += step
        data.append(OHLCV(
            date=date(2024, 1, 1) + timedelta(weeks=i),
            open=price - 1.0,
            high=price + 5.0,
            low=price - 3.0,
            close=price,
            volume=50000,
        ))
    return tuple(data)


def _make_stock_info(code: str = "005930", name: str = "삼성전자") -> StockInfo:
    return StockInfo(
        code=code,
        name=name,
        market="KOSPI",
        sector="전기전자",
    )


def _make_stock_data(
    daily_count: int = 60,
    weekly_count: int = 40,
) -> StockData:
    return StockData(
        info=_make_stock_info(),
        daily=_make_daily_data(daily_count),
        weekly=_make_weekly_data(weekly_count),
    )


class TestDetermineGrade:
    """순차 단계별 등급 결정 테스트."""

    def test_no_signal(self):
        assert _determine_grade(0) == ""

    def test_basic_buy(self):
        assert _determine_grade(1) == "기본매수"

    def test_reinforced_buy(self):
        assert _determine_grade(2) == "매수강화"

    def test_double_buy(self):
        assert _determine_grade(3) == "이중매수"

    def test_complete_buy(self):
        assert _determine_grade(4) == "완전매수"


class TestScreenStock:
    """단일 종목 스크리닝 테스트."""

    def test_empty_daily_data(self):
        stock = StockData(
            info=_make_stock_info(),
            daily=(),
            weekly=_make_weekly_data(40),
        )
        result = screen_stock(stock)
        assert result is None

    def test_returns_none_or_signal(self):
        stock = _make_stock_data()
        result = screen_stock(stock)
        assert result is None or isinstance(result, DreamTeamSignal)

    def test_signal_has_correct_stock_info(self):
        stock = _make_stock_data()
        result = screen_stock(stock)
        if result is not None:
            assert result.stock_info == stock.info

    def test_signal_strength_range(self):
        stock = _make_stock_data()
        result = screen_stock(stock)
        if result is not None:
            assert 1 <= result.signal_strength <= 4

    def test_signal_grade_valid(self):
        stock = _make_stock_data()
        result = screen_stock(stock)
        if result is not None:
            assert result.signal_grade in (
                "기본매수", "매수강화", "이중매수", "완전매수",
            )

    def test_signal_date_is_last_daily_date(self):
        stock = _make_stock_data()
        result = screen_stock(stock)
        if result is not None:
            assert result.date == stock.daily[-1].date

    def test_short_data_returns_none(self):
        stock = StockData(
            info=_make_stock_info(),
            daily=_make_daily_data(5),
            weekly=_make_weekly_data(5),
        )
        result = screen_stock(stock)
        assert result is None

    def test_custom_parameters(self):
        stock = _make_stock_data(daily_count=80, weekly_count=50)
        custom = DreamIndexConfig(
            dmi=DMIConfig(period=7),
            stochastic=StochasticConfig(k=5, d=3, slowing=3),
        )
        result = screen_stock(stock, config=custom)
        assert result is None or isinstance(result, DreamTeamSignal)

    def test_sequential_stage_consistency(self):
        """signal_strength는 DMI→스토캐스틱→채킨→MACD 순차 단계를 반영한다."""
        stock = _make_stock_data()
        result = screen_stock(stock)
        if result is None:
            return

        expected_stage = 0
        if result.dmi_signal:
            expected_stage = 1
            if result.stochastic_signal:
                expected_stage = 2
                if result.chaikin_signal:
                    expected_stage = 3
                    if result.macd_signal:
                        expected_stage = 4
        assert result.signal_strength == expected_stage


class TestScreenAll:
    """전 종목 스크리닝 테스트."""

    def test_empty_list(self):
        result = screen_all([])
        assert result == []

    def test_returns_list(self):
        stocks = [_make_stock_data()]
        result = screen_all(stocks)
        assert isinstance(result, list)

    def test_sorted_by_strength_descending(self):
        stocks = [
            StockData(
                info=StockInfo(code=f"00{i:04d}", name=f"종목{i}", market="KOSPI", sector="기타"),
                daily=_make_daily_data(60),
                weekly=_make_weekly_data(40),
            )
            for i in range(5)
        ]
        result = screen_all(stocks)
        if len(result) > 1:
            strengths = [s.signal_strength for s in result]
            assert strengths == sorted(strengths, reverse=True)

    def test_filters_none_signals(self):
        stocks = [
            StockData(
                info=_make_stock_info(),
                daily=_make_daily_data(3),
                weekly=_make_weekly_data(3),
            ),
        ]
        result = screen_all(stocks)
        for signal in result:
            assert signal.signal_strength > 0

    def test_handles_error_gracefully(self):
        """오류 발생 종목은 건너뜀."""
        stocks = [
            _make_stock_data(),
            StockData(
                info=_make_stock_info(code="999999", name="오류종목"),
                daily=(),
                weekly=(),
            ),
        ]
        result = screen_all(stocks)
        assert isinstance(result, list)


class TestScreenStockEdgeCases:
    """스크리닝 엔진 엣지 케이스 테스트."""

    def test_none_values_throughout(self):
        """None 값이 많은 데이터."""
        daily = []
        for i in range(60):
            if i % 5 == 0:
                daily.append(OHLCV(
                    date=date(2024, 1, 1) + timedelta(days=i),
                    open=None, high=None, low=None, close=None, volume=None,
                ))
            else:
                price = 100.0 + i
                daily.append(OHLCV(
                    date=date(2024, 1, 1) + timedelta(days=i),
                    open=price, high=price + 2, low=price - 2, close=price, volume=10000,
                ))
        weekly = _make_weekly_data(40)
        stock = StockData(info=_make_stock_info(), daily=tuple(daily), weekly=weekly)
        result = screen_stock(stock)
        assert result is None or isinstance(result, DreamTeamSignal)

    def test_immutability(self):
        stock = _make_stock_data()
        original_daily = stock.daily
        original_weekly = stock.weekly
        screen_stock(stock)
        assert stock.daily is original_daily
        assert stock.weekly is original_weekly
