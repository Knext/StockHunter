"""타입 모듈 단위 테스트.

불변성, 생성, 동등성 등을 검증합니다.
"""

import pytest
from datetime import date

from src.types.stock import StockInfo
from src.types.ohlcv import OHLCV, StockData


class TestStockInfo:
    """StockInfo 데이터클래스 테스트."""

    def test_create(self):
        info = StockInfo(code="005930", name="삼성전자", market="KOSPI", sector="전기전자")
        assert info.code == "005930"
        assert info.name == "삼성전자"
        assert info.market == "KOSPI"
        assert info.sector == "전기전자"

    def test_frozen_immutability(self):
        info = StockInfo(code="005930", name="삼성전자", market="KOSPI", sector="전기전자")
        with pytest.raises(AttributeError):
            info.name = "변경시도"

    def test_equality(self):
        info1 = StockInfo(code="005930", name="삼성전자", market="KOSPI", sector="전기전자")
        info2 = StockInfo(code="005930", name="삼성전자", market="KOSPI", sector="전기전자")
        assert info1 == info2

    def test_inequality(self):
        info1 = StockInfo(code="005930", name="삼성전자", market="KOSPI", sector="전기전자")
        info2 = StockInfo(code="000660", name="SK하이닉스", market="KOSPI", sector="전기전자")
        assert info1 != info2


class TestOHLCV:
    """OHLCV 데이터클래스 테스트."""

    def test_create(self):
        candle = OHLCV(
            date=date(2024, 1, 2),
            open=75000.0,
            high=76000.0,
            low=74000.0,
            close=75500.0,
            volume=10000000,
        )
        assert candle.date == date(2024, 1, 2)
        assert candle.open == 75000.0
        assert candle.close == 75500.0
        assert candle.volume == 10000000

    def test_frozen_immutability(self):
        candle = OHLCV(
            date=date(2024, 1, 2),
            open=75000.0,
            high=76000.0,
            low=74000.0,
            close=75500.0,
            volume=10000000,
        )
        with pytest.raises(AttributeError):
            candle.close = 80000.0

    def test_none_values_preserved(self):
        """0 대신 None으로 데이터 없음을 표현합니다."""
        candle = OHLCV(
            date=date(2024, 1, 2),
            open=None,
            high=None,
            low=None,
            close=None,
            volume=None,
        )
        assert candle.open is None
        assert candle.high is None
        assert candle.low is None
        assert candle.close is None
        assert candle.volume is None

    def test_equality(self):
        candle1 = OHLCV(date=date(2024, 1, 2), open=100.0, high=110.0, low=90.0, close=105.0, volume=1000)
        candle2 = OHLCV(date=date(2024, 1, 2), open=100.0, high=110.0, low=90.0, close=105.0, volume=1000)
        assert candle1 == candle2


class TestStockData:
    """StockData 데이터클래스 테스트."""

    def _make_stock_data(self) -> StockData:
        info = StockInfo(code="005930", name="삼성전자", market="KOSPI", sector="전기전자")
        daily = (
            OHLCV(date=date(2024, 1, 2), open=75000.0, high=76000.0, low=74000.0, close=75500.0, volume=10000000),
            OHLCV(date=date(2024, 1, 3), open=75500.0, high=77000.0, low=75000.0, close=76500.0, volume=12000000),
        )
        weekly = (
            OHLCV(date=date(2024, 1, 5), open=75000.0, high=77000.0, low=74000.0, close=76500.0, volume=22000000),
        )
        return StockData(info=info, daily=daily, weekly=weekly)

    def test_create(self):
        data = self._make_stock_data()
        assert data.info.code == "005930"
        assert len(data.daily) == 2
        assert len(data.weekly) == 1

    def test_frozen_immutability(self):
        data = self._make_stock_data()
        with pytest.raises(AttributeError):
            data.info = StockInfo(code="000660", name="SK", market="KOSPI", sector="")

    def test_daily_is_tuple(self):
        data = self._make_stock_data()
        assert isinstance(data.daily, tuple)
        assert isinstance(data.weekly, tuple)

    def test_empty_data(self):
        info = StockInfo(code="999999", name="없는종목", market="KOSPI", sector="")
        data = StockData(info=info, daily=(), weekly=())
        assert len(data.daily) == 0
        assert len(data.weekly) == 0
