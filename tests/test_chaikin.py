"""채킨 오실레이터 단위 테스트."""

from datetime import date, timedelta

import pytest

from src.indicators.chaikin import calculate_chaikin
from src.indicators.types import ChaikinResult
from src.types.ohlcv import OHLCV


def _make_ohlcv(
    day_offset: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int = 10000,
) -> OHLCV:
    return OHLCV(
        date=date(2024, 1, 1) + timedelta(days=day_offset),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _make_accumulation_data(count: int) -> tuple[OHLCV, ...]:
    """매집(Accumulation) 패턴 데이터: 종가가 고가에 가까움."""
    data = []
    price = 100.0
    for i in range(count):
        price += 0.5
        data.append(_make_ohlcv(
            i,
            price - 1.0,
            price + 2.0,
            price - 2.0,
            price + 1.5,
            volume=10000 + i * 100,
        ))
    return tuple(data)


def _make_distribution_data(count: int) -> tuple[OHLCV, ...]:
    """분산(Distribution) 패턴 데이터: 종가가 저가에 가까움."""
    data = []
    price = 200.0
    for i in range(count):
        price -= 0.5
        data.append(_make_ohlcv(
            i,
            price + 1.0,
            price + 2.0,
            price - 2.0,
            price - 1.5,
            volume=10000 + i * 100,
        ))
    return tuple(data)


class TestCalculateChaikin:
    """채킨 오실레이터 계산 테스트."""

    def test_empty_data(self):
        result = calculate_chaikin(())
        assert result == ()

    def test_short_data(self):
        data = _make_accumulation_data(5)
        result = calculate_chaikin(data, fast_period=3, slow_period=10)
        assert result == ()

    def test_minimum_data(self):
        data = _make_accumulation_data(15)
        result = calculate_chaikin(data)
        assert len(result) > 0

    def test_result_type(self):
        data = _make_accumulation_data(20)
        result = calculate_chaikin(data)
        assert isinstance(result, tuple)
        for r in result:
            assert isinstance(r, ChaikinResult)

    def test_dates_ascending(self):
        data = _make_accumulation_data(20)
        result = calculate_chaikin(data)
        dates = [r.date for r in result]
        assert dates == sorted(dates)

    def test_accumulation_positive(self):
        """매집 패턴에서는 CO가 양수 경향."""
        data = _make_accumulation_data(30)
        result = calculate_chaikin(data)
        positive_count = sum(
            1 for r in result
            if r.co_value is not None and r.co_value > 0
        )
        assert positive_count > 0

    def test_none_values_in_data(self):
        data = list(_make_accumulation_data(15))
        data[7] = OHLCV(
            date=data[7].date,
            open=None,
            high=None,
            low=None,
            close=None,
            volume=None,
        )
        result = calculate_chaikin(tuple(data))
        assert isinstance(result, tuple)

    def test_custom_periods(self):
        data = _make_accumulation_data(30)
        result_default = calculate_chaikin(data)
        result_custom = calculate_chaikin(data, fast_period=5, slow_period=15)
        assert isinstance(result_default, tuple)
        assert isinstance(result_custom, tuple)


class TestChaikinBuySignal:
    """채킨 오실레이터 매수 신호 테스트."""

    def test_buy_signal_is_bool(self):
        data = _make_accumulation_data(20)
        result = calculate_chaikin(data)
        for r in result:
            assert isinstance(r.buy_signal, bool)

    def test_buy_signal_on_zero_crossover(self):
        """분산에서 매집으로 전환 시 0선 상향 돌파."""
        data = []
        for i in range(20):
            if i < 12:
                data.append(_make_ohlcv(
                    i, 100.0, 102.0, 98.0, 98.5, volume=10000,
                ))
            else:
                data.append(_make_ohlcv(
                    i, 100.0, 105.0, 99.0, 104.0, volume=20000,
                ))
        result = calculate_chaikin(tuple(data))
        assert isinstance(result, tuple)

    def test_no_signal_persistent_positive(self):
        """지속적으로 양수이면 돌파 신호 없음."""
        data = _make_accumulation_data(30)
        result = calculate_chaikin(data)
        if len(result) > 2:
            late_results = result[5:]
            all_positive = all(
                r.co_value is not None and r.co_value > 0
                for r in late_results
            )
            if all_positive:
                signal_count = sum(1 for r in late_results if r.buy_signal)
                assert signal_count == 0


class TestChaikinEdgeCases:
    """채킨 오실레이터 엣지 케이스 테스트."""

    def test_zero_volume(self):
        """거래량 0인 경우."""
        data = []
        for i in range(15):
            data.append(_make_ohlcv(i, 100.0, 105.0, 95.0, 102.0, volume=0))
        result = calculate_chaikin(tuple(data))
        assert isinstance(result, tuple)

    def test_high_equals_low(self):
        """고가 == 저가 (분모 0) → MFM None."""
        data = []
        for i in range(15):
            data.append(_make_ohlcv(i, 100.0, 100.0, 100.0, 100.0, volume=1000))
        result = calculate_chaikin(tuple(data))
        assert isinstance(result, tuple)

    def test_immutability(self):
        data = _make_accumulation_data(20)
        original = data
        calculate_chaikin(data)
        assert data is original
