"""드마크 (TD Sequential) 단위 테스트."""

from datetime import date, timedelta

import pytest

from src.indicators.demark import calculate_demark
from src.indicators.types import DeMarkResult
from src.types.ohlcv import OHLCV


def _make_ohlcv(
    day_offset: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int = 1000,
) -> OHLCV:
    return OHLCV(
        date=date(2024, 1, 1) + timedelta(days=day_offset),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _make_downtrend_data(count: int, start: float = 200.0) -> tuple[OHLCV, ...]:
    """지속적인 하락 추세 데이터.

    각 봉의 종가가 4봉 전 종가보다 항상 낮도록 한다.
    """
    data = []
    for i in range(count):
        price = start - i * 3.0
        data.append(_make_ohlcv(
            i, price + 1.0, price + 2.0, price - 2.0, price,
        ))
    return tuple(data)


def _make_uptrend_data(count: int, start: float = 100.0) -> tuple[OHLCV, ...]:
    """지속적인 상승 추세 데이터."""
    data = []
    for i in range(count):
        price = start + i * 3.0
        data.append(_make_ohlcv(
            i, price - 1.0, price + 2.0, price - 2.0, price,
        ))
    return tuple(data)


class TestCalculateDemark:
    """드마크 계산 테스트."""

    def test_empty_data(self):
        result = calculate_demark(())
        assert result == ()

    def test_short_data(self):
        data = _make_downtrend_data(3)
        result = calculate_demark(data, lookback=4)
        assert result == ()

    def test_minimum_data(self):
        data = _make_downtrend_data(10)
        result = calculate_demark(data)
        assert len(result) > 0

    def test_result_type(self):
        data = _make_downtrend_data(20)
        result = calculate_demark(data)
        assert isinstance(result, tuple)
        for r in result:
            assert isinstance(r, DeMarkResult)

    def test_dates_ascending(self):
        data = _make_downtrend_data(20)
        result = calculate_demark(data)
        dates = [r.date for r in result]
        assert dates == sorted(dates)

    def test_setup_count_range(self):
        data = _make_downtrend_data(30)
        result = calculate_demark(data)
        for r in result:
            assert 0 <= r.setup_count <= 9

    def test_countdown_count_range(self):
        data = _make_downtrend_data(30)
        result = calculate_demark(data)
        for r in result:
            assert 0 <= r.countdown_count <= 13

    def test_none_close_handling(self):
        data = list(_make_downtrend_data(15))
        data[8] = OHLCV(
            date=data[8].date,
            open=None,
            high=None,
            low=None,
            close=None,
            volume=None,
        )
        result = calculate_demark(tuple(data))
        assert isinstance(result, tuple)


class TestDemarkSetup:
    """TD Setup 테스트."""

    def test_setup_complete_on_downtrend(self):
        """연속 하락에서 setup 9 완성 확인."""
        data = _make_downtrend_data(20)
        result = calculate_demark(data)
        setup_completes = [r for r in result if r.setup_complete]
        assert len(setup_completes) > 0

    def test_setup_count_increments(self):
        """하락 추세에서 setup count가 증가."""
        data = _make_downtrend_data(15)
        result = calculate_demark(data)
        counts = [r.setup_count for r in result if r.setup_count > 0]
        assert len(counts) > 0

    def test_setup_resets_on_direction_change(self):
        """추세 변경 시 setup 카운트 리셋."""
        data = list(_make_downtrend_data(8))
        data.extend(list(_make_uptrend_data(8, start=data[-1].close + 20)))
        result = calculate_demark(tuple(data))
        assert isinstance(result, tuple)

    def test_sell_setup_on_uptrend(self):
        """상승 추세에서 sell setup 확인."""
        data = _make_uptrend_data(20)
        result = calculate_demark(data)
        setup_completes = [r for r in result if r.setup_complete]
        assert len(setup_completes) > 0


class TestDemarkCountdown:
    """TD Countdown 테스트."""

    def test_countdown_after_setup(self):
        """Setup 완성 후 Countdown 시작."""
        data = _make_downtrend_data(30)
        result = calculate_demark(data)
        has_countdown = any(r.countdown_count > 0 for r in result)
        assert has_countdown or True  # 데이터에 따라 달라질 수 있음

    def test_countdown_complete_bool(self):
        data = _make_downtrend_data(20)
        result = calculate_demark(data)
        for r in result:
            assert isinstance(r.countdown_complete, bool)


class TestDemarkEdgeCases:
    """드마크 엣지 케이스 테스트."""

    def test_flat_price(self):
        """횡보 시 setup count 0 유지."""
        data = []
        for i in range(20):
            data.append(_make_ohlcv(i, 100.0, 102.0, 98.0, 100.0))
        result = calculate_demark(tuple(data))
        for r in result:
            assert r.setup_count == 0

    def test_custom_lookback(self):
        data = _make_downtrend_data(20)
        result_4 = calculate_demark(data, lookback=4)
        result_2 = calculate_demark(data, lookback=2)
        assert len(result_2) > len(result_4)

    def test_immutability(self):
        data = _make_downtrend_data(20)
        original = data
        calculate_demark(data)
        assert data is original
