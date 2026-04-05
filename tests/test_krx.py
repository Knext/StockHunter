"""KRX 데이터 수집 모듈 단위 테스트.

pykrx API를 모킹하여 테스트합니다.
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

import pandas as pd

from src.config import Config
from src.data.krx import (
    get_daily_ohlcv,
    get_weekly_ohlcv,
    get_stock_data,
    _daily_to_weekly,
    _parse_ohlcv_row,
)
from src.types.ohlcv import OHLCV, StockData
from src.types.stock import StockInfo

TEST_CONFIG = Config(
    cache_dir=".cache_test",
    cache_ttl_hours=24,
    rate_limit_seconds=0.0,
)


def _make_ohlcv_df(rows: list[dict]) -> pd.DataFrame:
    """테스트용 OHLCV DataFrame을 생성합니다."""
    df = pd.DataFrame(rows)
    df.index = pd.to_datetime(df["date"])
    df = df.drop(columns=["date"])
    return df


class TestParseOhlcvRow:
    """_parse_ohlcv_row 함수 테스트."""

    def test_normal_values(self):
        row = pd.Series({"시가": 75000, "고가": 76000, "저가": 74000, "종가": 75500, "거래량": 10000000})
        result = _parse_ohlcv_row(date(2024, 1, 2), row)

        assert result.date == date(2024, 1, 2)
        assert result.open == 75000.0
        assert result.high == 76000.0
        assert result.low == 74000.0
        assert result.close == 75500.0
        assert result.volume == 10000000

    def test_zero_values_become_none(self):
        """0 값은 데이터 없음으로 처리되어 None이 됩니다."""
        row = pd.Series({"시가": 0, "고가": 0, "저가": 0, "종가": 0, "거래량": 0})
        result = _parse_ohlcv_row(date(2024, 1, 2), row)

        assert result.open is None
        assert result.high is None
        assert result.low is None
        assert result.close is None
        assert result.volume is None


class TestDailyToWeekly:
    """_daily_to_weekly 변환 함수 테스트."""

    def test_empty_input(self):
        assert _daily_to_weekly(()) == ()

    def test_single_week(self):
        daily = (
            OHLCV(date=date(2024, 1, 2), open=100.0, high=110.0, low=90.0, close=105.0, volume=1000),
            OHLCV(date=date(2024, 1, 3), open=105.0, high=115.0, low=95.0, close=110.0, volume=1500),
            OHLCV(date=date(2024, 1, 4), open=110.0, high=120.0, low=100.0, close=115.0, volume=2000),
            OHLCV(date=date(2024, 1, 5), open=115.0, high=118.0, low=108.0, close=112.0, volume=1200),
        )
        weekly = _daily_to_weekly(daily)

        assert len(weekly) == 1
        assert weekly[0].open == 100.0
        assert weekly[0].high == 120.0
        assert weekly[0].low == 90.0
        assert weekly[0].close == 112.0
        assert weekly[0].volume == 5700

    def test_two_weeks(self):
        daily = (
            OHLCV(date=date(2024, 1, 2), open=100.0, high=110.0, low=90.0, close=105.0, volume=1000),
            OHLCV(date=date(2024, 1, 3), open=105.0, high=115.0, low=95.0, close=110.0, volume=1500),
            OHLCV(date=date(2024, 1, 8), open=110.0, high=125.0, low=105.0, close=120.0, volume=2000),
            OHLCV(date=date(2024, 1, 9), open=120.0, high=130.0, low=115.0, close=125.0, volume=2500),
        )
        weekly = _daily_to_weekly(daily)

        assert len(weekly) == 2
        # 첫째 주
        assert weekly[0].open == 100.0
        assert weekly[0].high == 115.0
        assert weekly[0].close == 110.0
        # 둘째 주
        assert weekly[1].open == 110.0
        assert weekly[1].high == 130.0
        assert weekly[1].close == 125.0

    def test_none_values_handled(self):
        daily = (
            OHLCV(date=date(2024, 1, 2), open=None, high=None, low=None, close=None, volume=None),
            OHLCV(date=date(2024, 1, 3), open=100.0, high=110.0, low=90.0, close=105.0, volume=1000),
        )
        weekly = _daily_to_weekly(daily)

        assert len(weekly) == 1
        assert weekly[0].open is None
        assert weekly[0].high == 110.0
        assert weekly[0].low == 90.0
        assert weekly[0].close == 105.0
        assert weekly[0].volume == 1000


class TestGetDailyOhlcv:
    """get_daily_ohlcv 함수 테스트."""

    @patch("src.data.krx.stock.get_market_ohlcv_by_date")
    def test_returns_ohlcv_tuple(self, mock_api):
        df = _make_ohlcv_df([
            {"date": "2024-01-02", "시가": 75000, "고가": 76000, "저가": 74000, "종가": 75500, "거래량": 10000000},
            {"date": "2024-01-03", "시가": 75500, "고가": 77000, "저가": 75000, "종가": 76500, "거래량": 12000000},
        ])
        mock_api.return_value = df

        result = get_daily_ohlcv("005930", "20240102", "20240103", TEST_CONFIG)

        assert len(result) == 2
        assert isinstance(result, tuple)
        assert result[0].date == date(2024, 1, 2)
        assert result[1].close == 76500.0
        mock_api.assert_called_once_with("20240102", "20240103", "005930")

    @patch("src.data.krx.stock.get_market_ohlcv_by_date")
    def test_empty_dataframe(self, mock_api):
        mock_api.return_value = pd.DataFrame()

        result = get_daily_ohlcv("999999", "20240102", "20240103", TEST_CONFIG)

        assert result == ()


class TestGetWeeklyOhlcv:
    """get_weekly_ohlcv 함수 테스트."""

    @patch("src.data.krx.stock.get_market_ohlcv_by_date")
    def test_converts_daily_to_weekly(self, mock_api):
        df = _make_ohlcv_df([
            {"date": "2024-01-02", "시가": 100, "고가": 110, "저가": 90, "종가": 105, "거래량": 1000},
            {"date": "2024-01-03", "시가": 105, "고가": 115, "저가": 95, "종가": 110, "거래량": 1500},
            {"date": "2024-01-04", "시가": 110, "고가": 120, "저가": 100, "종가": 115, "거래량": 2000},
        ])
        mock_api.return_value = df

        result = get_weekly_ohlcv("005930", "20240102", "20240104", TEST_CONFIG)

        assert len(result) == 1
        assert result[0].high == 120.0
        assert result[0].low == 90.0
        assert result[0].volume == 4500


class TestGetStockData:
    """get_stock_data 함수 테스트."""

    @patch("src.data.krx.stock.get_market_ohlcv_by_date")
    @patch("src.data.krx.stock.get_market_ticker_name")
    def test_returns_stock_data(self, mock_name, mock_ohlcv):
        mock_name.return_value = "삼성전자"
        df = _make_ohlcv_df([
            {"date": "2024-01-02", "시가": 75000, "고가": 76000, "저가": 74000, "종가": 75500, "거래량": 10000000},
        ])
        mock_ohlcv.return_value = df

        result = get_stock_data("005930", days=30, config=TEST_CONFIG)

        assert isinstance(result, StockData)
        assert result.info.code == "005930"
        assert result.info.name == "삼성전자"
        assert len(result.daily) == 1
        assert len(result.weekly) == 1
