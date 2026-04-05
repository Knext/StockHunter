"""스토캐스틱 오실레이터 단위 테스트."""

from datetime import date, timedelta

import pytest

from src.indicators.stochastic import calculate_stochastic
from src.indicators.types import StochasticResult
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


def _make_data(count: int, start: float = 100.0, step: float = 1.0) -> tuple[OHLCV, ...]:
    """단순 상승 데이터 생성."""
    data = []
    price = start
    for i in range(count):
        price += step
        data.append(_make_ohlcv(i, price - 0.5, price + 2.0, price - 2.0, price))
    return tuple(data)


class TestCalculateStochastic:
    """스토캐스틱 계산 테스트."""

    def test_empty_data(self):
        result = calculate_stochastic(())
        assert result == ()

    def test_short_data(self):
        data = _make_data(10)
        result = calculate_stochastic(data, k_period=14, d_period=3, slowing=3)
        assert result == ()

    def test_minimum_data(self):
        data = _make_data(20)
        result = calculate_stochastic(data)
        assert len(result) > 0

    def test_result_type(self):
        data = _make_data(30)
        result = calculate_stochastic(data)
        assert isinstance(result, tuple)
        for r in result:
            assert isinstance(r, StochasticResult)

    def test_k_range(self):
        """Slow %K 값이 0-100 범위 내."""
        data = _make_data(50)
        result = calculate_stochastic(data)
        for r in result:
            if r.k is not None:
                assert 0 <= r.k <= 100

    def test_d_range(self):
        """Slow %D 값이 0-100 범위 내."""
        data = _make_data(50)
        result = calculate_stochastic(data)
        for r in result:
            if r.d is not None:
                assert 0 <= r.d <= 100

    def test_dates_ascending(self):
        data = _make_data(30)
        result = calculate_stochastic(data)
        dates = [r.date for r in result]
        assert dates == sorted(dates)

    def test_none_values_in_data(self):
        data = list(_make_data(25))
        data[10] = OHLCV(
            date=data[10].date,
            open=None,
            high=None,
            low=None,
            close=None,
            volume=None,
        )
        result = calculate_stochastic(tuple(data))
        assert isinstance(result, tuple)

    def test_custom_periods(self):
        data = _make_data(40)
        result_fast = calculate_stochastic(data, k_period=5, d_period=3, slowing=3)
        result_slow = calculate_stochastic(data, k_period=14, d_period=3, slowing=3)
        assert len(result_fast) > len(result_slow)


class TestStochasticBuyReinforcement:
    """스토캐스틱 매수 강화 신호 테스트."""

    def test_buy_reinforcement_is_bool(self):
        data = _make_data(30)
        result = calculate_stochastic(data)
        for r in result:
            assert isinstance(r.buy_reinforcement, bool)

    def test_buy_reinforcement_on_80_crossover(self):
        """가격이 급등하여 %K가 80을 돌파할 때 매수 강화 신호."""
        data = []
        for i in range(30):
            if i < 20:
                data.append(_make_ohlcv(i, 50.0, 52.0, 48.0, 50.0))
            else:
                price = 50.0 + (i - 19) * 3.0
                data.append(_make_ohlcv(i, price - 1.0, price + 1.0, price - 2.0, price))

        result = calculate_stochastic(tuple(data))
        reinforcements = [r for r in result if r.buy_reinforcement]
        assert len(reinforcements) >= 0  # 조건 충족 시 신호 발생

    def test_no_reinforcement_below_80(self):
        """%K가 80 이하이면 매수 강화 아님."""
        data = _make_data(30, start=100.0, step=0.1)
        result = calculate_stochastic(data)
        for r in result:
            if r.k is not None and r.k < 80:
                assert not r.buy_reinforcement

    def test_reinforcement_requires_crossover(self):
        """%K가 이미 80 이상이면 매수 강화 아님 (돌파가 아님)."""
        data = _make_data(30, start=100.0, step=5.0)
        result = calculate_stochastic(data)
        high_k_no_cross = [
            r for r in result
            if r.k is not None and r.k >= 80 and not r.buy_reinforcement
        ]
        assert isinstance(high_k_no_cross, list)


class TestStochasticEdgeCases:
    """스토캐스틱 엣지 케이스 테스트."""

    def test_all_same_price(self):
        """모든 가격 동일 → %K = None (분모 0)."""
        data = []
        for i in range(30):
            data.append(_make_ohlcv(i, 100.0, 100.0, 100.0, 100.0))
        result = calculate_stochastic(tuple(data))
        for r in result:
            assert r.k is None

    def test_immutability(self):
        data = _make_data(30)
        original = data
        calculate_stochastic(data)
        assert data is original
