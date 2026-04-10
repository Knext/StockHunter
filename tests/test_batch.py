"""배치 스크리닝 파이프라인 테스트."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.batch.runner import run_batch, _split_into_batches
from src.batch.types import BatchResult
from src.screener.types import DreamTeamSignal
from src.types.ohlcv import OHLCV, StockData
from src.types.stock import StockInfo


def _make_stock_info(code: str, name: str = "테스트") -> StockInfo:
    return StockInfo(code=code, name=name, market="KOSPI", sector="기타")


def _make_ohlcv(day: int) -> OHLCV:
    return OHLCV(
        date=date(2024, 1, day),
        open=100.0,
        high=110.0,
        low=90.0,
        close=105.0,
        volume=10000,
    )


def _make_stock_data(code: str) -> StockData:
    daily = tuple(_make_ohlcv(d) for d in range(1, 21))
    weekly = tuple(_make_ohlcv(d) for d in [1, 8, 15])
    return StockData(
        info=_make_stock_info(code),
        daily=daily,
        weekly=weekly,
    )


def _make_signal(code: str, strength: int) -> DreamTeamSignal:
    return DreamTeamSignal(
        stock_info=_make_stock_info(code),
        date=date(2024, 1, 20),
        dmi_signal=strength >= 1,
        stochastic_signal=strength >= 2,
        chaikin_signal=strength >= 3,
        macd_signal=strength >= 4,
        demark_signal=False,
        signal_strength=strength,
        signal_grade="기본매수",
    )


class TestSplitIntoBatches:
    """_split_into_batches 유틸리티 테스트."""

    def test_even_split(self):
        items = [_make_stock_info(f"{i:06d}") for i in range(6)]
        batches = _split_into_batches(items, 3)
        assert len(batches) == 2
        assert len(batches[0]) == 3
        assert len(batches[1]) == 3

    def test_uneven_split(self):
        items = [_make_stock_info(f"{i:06d}") for i in range(5)]
        batches = _split_into_batches(items, 3)
        assert len(batches) == 2
        assert len(batches[0]) == 3
        assert len(batches[1]) == 2

    def test_empty_list(self):
        batches = _split_into_batches([], 10)
        assert batches == []

    def test_single_batch(self):
        items = [_make_stock_info(f"{i:06d}") for i in range(3)]
        batches = _split_into_batches(items, 10)
        assert len(batches) == 1
        assert len(batches[0]) == 3


class TestRunBatch:
    """run_batch 통합 테스트 (모킹)."""

    @pytest.mark.asyncio
    async def test_basic_screening(self):
        """정상 흐름: 전 종목 스크리닝 후 시그널 반환."""
        stocks = [_make_stock_info("000001"), _make_stock_info("000002")]
        stock_data_map = {
            "000001": _make_stock_data("000001"),
            "000002": _make_stock_data("000002"),
        }

        with (
            patch("src.batch.runner.get_index_data", return_value=_make_stock_data("KS11")),
            patch("src.batch.runner.get_all_stocks", return_value=stocks),
            patch("src.batch.runner.load_config"),
            patch("src.batch.runner.CachedDataFetcher") as mock_fetcher_cls,
            patch(
                "src.batch.runner.screen_stock",
                side_effect=[
                    _make_signal("000001", 3),
                    _make_signal("000002", 1),
                ],
            ),
        ):
            mock_fetcher = MagicMock()
            mock_fetcher.get_stock_data.side_effect = lambda code, days: stock_data_map[code]
            mock_fetcher_cls.return_value = mock_fetcher

            result = await run_batch(market="KOSPI", batch_size=10, max_concurrent=2)

        assert isinstance(result, BatchResult)
        assert result.total_stocks == 2
        assert result.success_count == 2
        assert len(result.signals) == 2
        assert len(result.failed_codes) == 0
        assert result.market == "KOSPI"
        # signal_strength 내림차순 정렬 확인
        assert result.signals[0].signal_strength >= result.signals[1].signal_strength

    @pytest.mark.asyncio
    async def test_partial_failure(self):
        """부분 실패: 일부 종목 Exception 시 스킵하고 나머지 처리."""
        stocks = [
            _make_stock_info("000001"),
            _make_stock_info("000002"),
            _make_stock_info("000003"),
        ]

        def mock_get_stock_data(code, days):
            if code == "000002":
                raise RuntimeError("데이터 수집 실패")
            return _make_stock_data(code)

        with (
            patch("src.batch.runner.get_index_data", return_value=_make_stock_data("KS11")),
            patch("src.batch.runner.get_all_stocks", return_value=stocks),
            patch("src.batch.runner.load_config"),
            patch("src.batch.runner.CachedDataFetcher") as mock_fetcher_cls,
            patch(
                "src.batch.runner.screen_stock",
                return_value=_make_signal("000001", 2),
            ),
        ):
            mock_fetcher = MagicMock()
            mock_fetcher.get_stock_data.side_effect = mock_get_stock_data
            mock_fetcher_cls.return_value = mock_fetcher

            result = await run_batch(batch_size=10, max_concurrent=1)

        assert result.total_stocks == 3
        assert result.success_count == 2
        assert len(result.failed_codes) == 1
        assert "000002" in result.failed_codes

    @pytest.mark.asyncio
    async def test_empty_stock_list(self):
        """빈 종목 리스트: 빈 결과 반환."""
        with (
            patch("src.batch.runner.get_index_data", return_value=_make_stock_data("KS11")),
            patch("src.batch.runner.get_all_stocks", return_value=[]),
            patch("src.batch.runner.load_config"),
            patch("src.batch.runner.CachedDataFetcher"),
        ):
            result = await run_batch()

        assert result.total_stocks == 0
        assert result.success_count == 0
        assert len(result.signals) == 0
        assert len(result.failed_codes) == 0

    @pytest.mark.asyncio
    async def test_no_signals(self):
        """시그널 없음: screen_stock이 None 반환 시 빈 시그널."""
        stocks = [_make_stock_info("000001")]

        with (
            patch("src.batch.runner.get_index_data", return_value=_make_stock_data("KS11")),
            patch("src.batch.runner.get_all_stocks", return_value=stocks),
            patch("src.batch.runner.load_config"),
            patch("src.batch.runner.CachedDataFetcher") as mock_fetcher_cls,
            patch("src.batch.runner.screen_stock", return_value=None),
        ):
            mock_fetcher = MagicMock()
            mock_fetcher.get_stock_data.return_value = _make_stock_data("000001")
            mock_fetcher_cls.return_value = mock_fetcher

            result = await run_batch(batch_size=10)

        assert result.total_stocks == 1
        assert result.success_count == 1
        assert len(result.signals) == 0

    @pytest.mark.asyncio
    async def test_signal_strength_sorted_descending(self):
        """시그널이 signal_strength 내림차순으로 정렬되는지 확인."""
        stocks = [
            _make_stock_info("000001"),
            _make_stock_info("000002"),
            _make_stock_info("000003"),
        ]

        signals = [
            _make_signal("000001", 1),
            _make_signal("000002", 4),
            _make_signal("000003", 3),
        ]

        with (
            patch("src.batch.runner.get_index_data", return_value=_make_stock_data("KS11")),
            patch("src.batch.runner.get_all_stocks", return_value=stocks),
            patch("src.batch.runner.load_config"),
            patch("src.batch.runner.CachedDataFetcher") as mock_fetcher_cls,
            patch("src.batch.runner.screen_stock", side_effect=signals),
        ):
            mock_fetcher = MagicMock()
            mock_fetcher.get_stock_data.side_effect = lambda code, days: _make_stock_data(code)
            mock_fetcher_cls.return_value = mock_fetcher

            result = await run_batch(batch_size=10)

        strengths = [s.signal_strength for s in result.signals]
        assert strengths == [4, 3, 1]

    @pytest.mark.asyncio
    async def test_multiple_batches(self):
        """여러 배치로 분할하여 처리."""
        stocks = [_make_stock_info(f"{i:06d}") for i in range(5)]

        with (
            patch("src.batch.runner.get_index_data", return_value=_make_stock_data("KS11")),
            patch("src.batch.runner.get_all_stocks", return_value=stocks),
            patch("src.batch.runner.load_config"),
            patch("src.batch.runner.CachedDataFetcher") as mock_fetcher_cls,
            patch("src.batch.runner.screen_stock", return_value=None),
        ):
            mock_fetcher = MagicMock()
            mock_fetcher.get_stock_data.side_effect = lambda code, days: _make_stock_data(code)
            mock_fetcher_cls.return_value = mock_fetcher

            result = await run_batch(batch_size=2, max_concurrent=2)

        assert result.total_stocks == 5
        assert result.success_count == 5
        assert mock_fetcher.get_stock_data.call_count == 5

    @pytest.mark.asyncio
    async def test_batch_result_is_frozen(self):
        """BatchResult가 불변인지 확인."""
        with (
            patch("src.batch.runner.get_index_data", return_value=_make_stock_data("KS11")),
            patch("src.batch.runner.get_all_stocks", return_value=[]),
            patch("src.batch.runner.load_config"),
            patch("src.batch.runner.CachedDataFetcher"),
        ):
            result = await run_batch()

        with pytest.raises(AttributeError):
            result.total_stocks = 999
