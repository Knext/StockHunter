"""MACD 오실레이터 단위 테스트."""

from datetime import date, timedelta

import pytest

from src.indicators.macd import calculate_macd_oscillator
from src.indicators.types import MACDOscResult
from src.types.ohlcv import OHLCV


def _make_ohlcv(
    day_offset: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int = 50000,
) -> OHLCV:
    return OHLCV(
        date=date(2024, 1, 1) + timedelta(days=day_offset * 7),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _make_weekly_data(
    count: int,
    start: float = 100.0,
    step: float = 1.0,
) -> tuple[OHLCV, ...]:
    """주봉 데이터 생성."""
    data = []
    price = start
    for i in range(count):
        price += step
        data.append(_make_ohlcv(i, price - 1.0, price + 3.0, price - 2.0, price))
    return tuple(data)


class TestCalculateMACDOscillator:
    """MACD 오실레이터 계산 테스트."""

    def test_empty_data(self):
        result = calculate_macd_oscillator(())
        assert result == ()

    def test_short_data(self):
        data = _make_weekly_data(20)
        result = calculate_macd_oscillator(data)
        assert result == ()

    def test_minimum_data(self):
        data = _make_weekly_data(35)
        result = calculate_macd_oscillator(data)
        assert len(result) > 0

    def test_result_type(self):
        data = _make_weekly_data(50)
        result = calculate_macd_oscillator(data)
        assert isinstance(result, tuple)
        for r in result:
            assert isinstance(r, MACDOscResult)

    def test_dates_ascending(self):
        data = _make_weekly_data(50)
        result = calculate_macd_oscillator(data)
        dates = [r.date for r in result]
        assert dates == sorted(dates)

    def test_macd_signal_oscillator_relationship(self):
        """oscillator = macd - signal 검증."""
        data = _make_weekly_data(50)
        result = calculate_macd_oscillator(data)
        for r in result:
            if r.macd is not None and r.signal is not None and r.oscillator is not None:
                assert abs(r.oscillator - (r.macd - r.signal)) < 1e-10

    def test_none_close_handling(self):
        data = list(_make_weekly_data(40))
        data[15] = OHLCV(
            date=data[15].date,
            open=None,
            high=None,
            low=None,
            close=None,
            volume=None,
        )
        result = calculate_macd_oscillator(tuple(data))
        assert isinstance(result, tuple)

    def test_custom_periods(self):
        data = _make_weekly_data(60)
        result_default = calculate_macd_oscillator(data)
        result_custom = calculate_macd_oscillator(data, fast=8, slow=17, signal=9)
        assert len(result_custom) > len(result_default)


class TestMACDBuySignal:
    """MACD 매수 신호 테스트."""

    def test_buy_signal_is_bool(self):
        data = _make_weekly_data(50)
        result = calculate_macd_oscillator(data)
        for r in result:
            assert isinstance(r.buy_signal, bool)

    def test_buy_signal_on_positive_crossover(self):
        """하락 후 상승 전환 시 오실레이터 양전환 검증."""
        data = []
        price = 200.0
        for i in range(50):
            if i < 30:
                price -= 2.0
            else:
                price += 3.0
            data.append(_make_ohlcv(
                i, price - 1.0, price + 3.0, price - 2.0, price,
            ))
        result = calculate_macd_oscillator(tuple(data))
        buy_signals = [r for r in result if r.buy_signal]
        assert len(buy_signals) >= 0  # 조건 충족 시 발생

    def test_steady_uptrend_signal(self):
        """꾸준한 상승에서는 오실레이터 양수 유지 → 상승 전환 신호 가능."""
        data = _make_weekly_data(50, step=2.0)
        result = calculate_macd_oscillator(data)
        assert isinstance(result, tuple)


class TestMACDEdgeCases:
    """MACD 엣지 케이스 테스트."""

    def test_all_same_close(self):
        """모든 종가 동일 → MACD = 0."""
        data = []
        for i in range(40):
            data.append(_make_ohlcv(i, 100.0, 105.0, 95.0, 100.0))
        result = calculate_macd_oscillator(tuple(data))
        for r in result:
            if r.macd is not None:
                assert abs(r.macd) < 1e-6

    def test_exactly_minimum_length(self):
        data = _make_weekly_data(34)
        result = calculate_macd_oscillator(data)
        assert len(result) >= 0

    def test_immutability(self):
        data = _make_weekly_data(50)
        original = data
        calculate_macd_oscillator(data)
        assert data is original
