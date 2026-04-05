"""DMI 지표 단위 테스트."""

from datetime import date, timedelta

import pytest

from src.indicators.dmi import calculate_dmi
from src.indicators.types import DMIResult
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


def _make_trending_data(count: int, start_price: float = 100.0) -> tuple[OHLCV, ...]:
    """상승 추세 데이터 생성."""
    data = []
    price = start_price
    for i in range(count):
        price += 1.0
        data.append(_make_ohlcv(
            i,
            price - 0.5,
            price + 2.0,
            price - 1.0,
            price,
        ))
    return tuple(data)


class TestCalculateDMI:
    """DMI 계산 테스트."""

    def test_empty_data(self):
        result = calculate_dmi(())
        assert result == ()

    def test_short_data(self):
        data = _make_trending_data(10)
        result = calculate_dmi(data, period=14)
        assert result == ()

    def test_minimum_data(self):
        data = _make_trending_data(30)
        result = calculate_dmi(data, period=14)
        assert len(result) > 0

    def test_result_type(self):
        data = _make_trending_data(50)
        result = calculate_dmi(data)
        assert isinstance(result, tuple)
        for r in result:
            assert isinstance(r, DMIResult)

    def test_dates_ascending(self):
        data = _make_trending_data(50)
        result = calculate_dmi(data)
        dates = [r.date for r in result]
        assert dates == sorted(dates)

    def test_di_values_non_negative(self):
        data = _make_trending_data(50)
        result = calculate_dmi(data)
        for r in result:
            if r.plus_di is not None:
                assert r.plus_di >= 0
            if r.minus_di is not None:
                assert r.minus_di >= 0

    def test_adx_range(self):
        data = _make_trending_data(80)
        result = calculate_dmi(data)
        for r in result:
            if r.adx is not None:
                assert 0 <= r.adx <= 100

    def test_none_values_in_data(self):
        """None 값이 포함된 데이터 처리."""
        data = list(_make_trending_data(30))
        data[5] = OHLCV(
            date=data[5].date,
            open=None,
            high=None,
            low=None,
            close=None,
            volume=None,
        )
        result = calculate_dmi(tuple(data))
        assert isinstance(result, tuple)

    def test_custom_period(self):
        data = _make_trending_data(50)
        result_7 = calculate_dmi(data, period=7)
        result_14 = calculate_dmi(data, period=14)
        assert len(result_7) > len(result_14)

    def test_buy_signal_is_bool(self):
        data = _make_trending_data(50)
        result = calculate_dmi(data)
        for r in result:
            assert isinstance(r.buy_signal, bool)


class TestDMIBuySignal:
    """DMI 매수 신호 조건 테스트."""

    def test_buy_signal_requires_adx_above_30(self):
        """ADX >= 30 조건 검증."""
        data = _make_trending_data(50)
        result = calculate_dmi(data)
        for r in result:
            if r.buy_signal:
                assert r.adx is not None
                assert r.adx >= 30

    def test_no_signal_with_flat_data(self):
        """횡보 데이터에서는 신호가 잘 발생하지 않음."""
        data = []
        for i in range(60):
            data.append(_make_ohlcv(
                i,
                100.0,
                101.0,
                99.0,
                100.0,
            ))
        result = calculate_dmi(tuple(data))
        signals = [r for r in result if r.buy_signal]
        assert len(signals) == 0

    def test_signal_with_downtrend_reversal(self):
        """하락 후 반전 시나리오에서 신호 확인.

        -DI가 높아졌다가 ADX 아래로 떨어지는 패턴을 만든다.
        """
        data = []
        price = 200.0
        for i in range(40):
            if i < 25:
                price -= 3.0
                data.append(_make_ohlcv(
                    i,
                    price + 1.0,
                    price + 2.0,
                    price - 3.0,
                    price,
                ))
            else:
                price += 2.0
                data.append(_make_ohlcv(
                    i,
                    price - 1.0,
                    price + 3.0,
                    price - 0.5,
                    price,
                ))

        result = calculate_dmi(tuple(data))
        assert isinstance(result, tuple)
        assert len(result) > 0


class TestDMIEdgeCases:
    """DMI 엣지 케이스 테스트."""

    def test_all_same_price(self):
        """모든 가격이 동일한 경우."""
        data = []
        for i in range(30):
            data.append(_make_ohlcv(i, 100.0, 100.0, 100.0, 100.0))
        result = calculate_dmi(tuple(data))
        assert isinstance(result, tuple)

    def test_single_candle(self):
        result = calculate_dmi((_make_ohlcv(0, 100, 105, 95, 102),))
        assert result == ()

    def test_exactly_period_plus_one(self):
        """period + 1개 데이터."""
        data = _make_trending_data(15)
        result = calculate_dmi(data, period=14)
        assert len(result) >= 1

    def test_immutability(self):
        """입력 데이터 불변성 확인."""
        data = _make_trending_data(30)
        original = data
        calculate_dmi(data)
        assert data is original
        assert data == original
