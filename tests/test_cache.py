"""캐시 모듈 단위 테스트.

캐시 히트, 미스, TTL 만료 시나리오를 검증합니다.
"""

import json
import pytest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.config import Config
from src.data.cache import (
    CachedDataFetcher,
    _ohlcv_to_dict,
    _dict_to_ohlcv,
    _stock_data_to_dict,
    _dict_to_stock_data,
    _make_cache_key,
)
from src.types.ohlcv import OHLCV, StockData
from src.types.stock import StockInfo


@pytest.fixture
def tmp_cache_dir(tmp_path):
    """임시 캐시 디렉토리를 생성합니다."""
    cache_dir = tmp_path / ".cache_test"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def test_config(tmp_cache_dir):
    """테스트용 설정을 반환합니다."""
    return Config(
        cache_dir=tmp_cache_dir,
        cache_ttl_hours=24,
        rate_limit_seconds=0.0,
    )


@pytest.fixture
def sample_ohlcv():
    return OHLCV(
        date=date(2024, 1, 2),
        open=75000.0,
        high=76000.0,
        low=74000.0,
        close=75500.0,
        volume=10000000,
    )


@pytest.fixture
def sample_stock_data():
    info = StockInfo(code="005930", name="삼성전자", market="KOSPI", sector="전기전자")
    daily = (
        OHLCV(date=date(2024, 1, 2), open=75000.0, high=76000.0, low=74000.0, close=75500.0, volume=10000000),
    )
    weekly = (
        OHLCV(date=date(2024, 1, 5), open=75000.0, high=76000.0, low=74000.0, close=75500.0, volume=10000000),
    )
    return StockData(info=info, daily=daily, weekly=weekly)


class TestSerialization:
    """직렬화/역직렬화 테스트."""

    def test_ohlcv_roundtrip(self, sample_ohlcv):
        data = _ohlcv_to_dict(sample_ohlcv)
        restored = _dict_to_ohlcv(data)
        assert restored == sample_ohlcv

    def test_ohlcv_none_values_roundtrip(self):
        candle = OHLCV(date=date(2024, 1, 2), open=None, high=None, low=None, close=None, volume=None)
        data = _ohlcv_to_dict(candle)
        restored = _dict_to_ohlcv(data)
        assert restored == candle
        assert restored.open is None

    def test_stock_data_roundtrip(self, sample_stock_data):
        data = _stock_data_to_dict(sample_stock_data)
        restored = _dict_to_stock_data(data)
        assert restored == sample_stock_data

    def test_cache_key_deterministic(self):
        key1 = _make_cache_key("daily", "005930", "20240102", "20240103")
        key2 = _make_cache_key("daily", "005930", "20240102", "20240103")
        assert key1 == key2

    def test_cache_key_unique(self):
        key1 = _make_cache_key("daily", "005930")
        key2 = _make_cache_key("daily", "000660")
        assert key1 != key2


class TestCachedDataFetcher:
    """CachedDataFetcher 클래스 테스트."""

    def test_creates_cache_directory(self, tmp_path):
        cache_dir = tmp_path / "new_cache"
        config = Config(cache_dir=cache_dir, cache_ttl_hours=24, rate_limit_seconds=0.0)
        fetcher = CachedDataFetcher(config)
        assert cache_dir.exists()

    @patch("src.data.cache.krx.get_stock_data")
    def test_cache_miss_calls_api(self, mock_api, test_config, sample_stock_data):
        mock_api.return_value = sample_stock_data
        fetcher = CachedDataFetcher(test_config)

        result = fetcher.get_stock_data("005930", days=200)

        assert result == sample_stock_data
        mock_api.assert_called_once()

    @patch("src.data.cache.krx.get_stock_data")
    def test_cache_hit_skips_api_when_today(self, mock_api, test_config):
        """캐시에 오늘 날짜 데이터가 있으면 API를 호출하지 않는다."""
        today = date.today()
        info = StockInfo(code="005930", name="삼성전자", market="KOSPI", sector="전기전자")
        daily = (
            OHLCV(date=today - timedelta(days=1), open=75000.0, high=76000.0, low=74000.0, close=75500.0, volume=10000000),
            OHLCV(date=today, open=76000.0, high=77000.0, low=75000.0, close=76500.0, volume=12000000),
        )
        fresh_data = StockData(info=info, daily=daily, weekly=daily)
        mock_api.return_value = fresh_data
        fetcher = CachedDataFetcher(test_config)

        # 첫 번째 호출: 캐시 미스
        fetcher.get_stock_data("005930", days=200)
        # 두 번째 호출: 캐시에 오늘 데이터 있으므로 API 스킵
        result = fetcher.get_stock_data("005930", days=200)

        assert result.daily[-1].date == today
        assert mock_api.call_count == 1

    @patch("src.data.cache.krx._rate_limit")
    @patch("src.data.cache.krx.stock.get_market_ticker_name", return_value="삼성전자")
    @patch("src.data.cache.krx.get_daily_ohlcv")
    @patch("src.data.cache.krx.get_stock_data")
    def test_incremental_fetch(self, mock_full, mock_daily, mock_name, mock_rate, test_config):
        """캐시에 어제까지 데이터가 있으면 오늘 데이터만 증분 조회한다."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        info = StockInfo(code="005930", name="삼성전자", market="KOSPI", sector="전기전자")

        old_daily = (
            OHLCV(date=yesterday, open=75000.0, high=76000.0, low=74000.0, close=75500.0, volume=10000000),
        )
        old_data = StockData(info=info, daily=old_daily, weekly=old_daily)
        mock_full.return_value = old_data

        new_candle = OHLCV(date=today, open=76000.0, high=77000.0, low=75000.0, close=76500.0, volume=12000000)
        mock_daily.return_value = (new_candle,)

        fetcher = CachedDataFetcher(test_config)

        # 첫 번째: 전체 조회
        fetcher.get_stock_data("005930", days=200)
        assert mock_full.call_count == 1

        # 두 번째: 증분 조회 (get_daily_ohlcv만 호출)
        result = fetcher.get_stock_data("005930", days=200)
        assert mock_full.call_count == 1  # 전체 조회 추가 없음
        assert mock_daily.call_count == 1  # 증분 조회 1회
        assert len(result.daily) == 2
        assert result.daily[-1].date == today

    @patch("src.data.cache.krx.get_daily_ohlcv")
    def test_daily_ohlcv_caching(self, mock_api, test_config, sample_ohlcv):
        mock_api.return_value = (sample_ohlcv,)
        fetcher = CachedDataFetcher(test_config)

        result1 = fetcher.get_daily_ohlcv("005930", "20240102", "20240103")
        result2 = fetcher.get_daily_ohlcv("005930", "20240102", "20240103")

        assert result1 == result2
        assert mock_api.call_count == 1

    @patch("src.data.cache.krx.get_weekly_ohlcv")
    def test_weekly_ohlcv_caching(self, mock_api, test_config, sample_ohlcv):
        mock_api.return_value = (sample_ohlcv,)
        fetcher = CachedDataFetcher(test_config)

        result1 = fetcher.get_weekly_ohlcv("005930", "20240102", "20240105")
        result2 = fetcher.get_weekly_ohlcv("005930", "20240102", "20240105")

        assert result1 == result2
        assert mock_api.call_count == 1

    def test_clear_cache(self, test_config, tmp_cache_dir):
        # 더미 캐시 파일 생성
        (tmp_cache_dir / "test1.json").write_text("{}")
        (tmp_cache_dir / "test2.json").write_text("{}")

        fetcher = CachedDataFetcher(test_config)
        deleted = fetcher.clear_cache()

        assert deleted == 2
        assert list(tmp_cache_dir.glob("*.json")) == []

    def test_corrupted_cache_handled(self, test_config, tmp_cache_dir):
        """손상된 캐시 파일은 무시되고 삭제됩니다."""
        cache_key = _make_cache_key("stock_data_v2", "005930")
        cache_file = tmp_cache_dir / f"{cache_key}.json"
        cache_file.write_text("invalid json{{{")

        fetcher = CachedDataFetcher(test_config)
        result = fetcher._read_cache_raw(cache_file)

        assert result is None
        assert not cache_file.exists()
