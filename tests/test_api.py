"""FastAPI REST API 통합 테스트."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.dependencies import get_config, get_fetcher
from src.config import Config
from src.types.ohlcv import OHLCV, StockData
from src.types.stock import StockInfo


def _make_daily(count: int = 200) -> tuple[OHLCV, ...]:
    """테스트용 일봉 데이터를 생성합니다."""
    base = date(2025, 1, 1).toordinal()
    return tuple(
        OHLCV(
            date=date.fromordinal(base + i),
            open=70000.0 + i * 10,
            high=71000.0 + i * 10,
            low=69000.0 + i * 10,
            close=70500.0 + i * 10,
            volume=1000000 + i * 100,
        )
        for i in range(count)
    )


def _make_weekly(daily: tuple[OHLCV, ...]) -> tuple[OHLCV, ...]:
    """일봉으로부터 주봉을 생성합니다."""
    weekly: list[OHLCV] = []
    for i in range(0, len(daily), 5):
        chunk = daily[i : i + 5]
        if not chunk:
            break
        highs = [c.high for c in chunk if c.high is not None]
        lows = [c.low for c in chunk if c.low is not None]
        volumes = [c.volume for c in chunk if c.volume is not None]
        weekly.append(
            OHLCV(
                date=chunk[-1].date,
                open=chunk[0].open,
                high=max(highs) if highs else None,
                low=min(lows) if lows else None,
                close=chunk[-1].close,
                volume=sum(volumes) if volumes else None,
            )
        )
    return tuple(weekly)


@pytest.fixture()
def mock_stock_info():
    return StockInfo(code="005930", name="삼성전자", market="KOSPI", sector="전기전자")


@pytest.fixture()
def mock_daily():
    return _make_daily()


@pytest.fixture()
def mock_weekly(mock_daily):
    return _make_weekly(mock_daily)


@pytest.fixture()
def mock_stock_data(mock_stock_info, mock_daily, mock_weekly):
    return StockData(info=mock_stock_info, daily=mock_daily, weekly=mock_weekly)


@pytest.fixture()
def mock_fetcher(mock_stock_data):
    fetcher = MagicMock()
    fetcher.get_stock_data.return_value = mock_stock_data
    return fetcher


@pytest.fixture()
def mock_config():
    from pathlib import Path
    return Config(cache_dir=Path(".cache"), cache_ttl_hours=24, rate_limit_seconds=0.5)


@pytest.fixture()
def client(mock_fetcher, mock_config):
    """의존성이 오버라이드된 테스트 클라이언트."""
    app = create_app()
    app.dependency_overrides[get_fetcher] = lambda: mock_fetcher
    app.dependency_overrides[get_config] = lambda: mock_config
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestScreenEndpoint:
    """GET /api/screen 테스트."""

    def test_screen_with_codes(self, client):
        """특정 종목 코드로 스크리닝합니다."""
        response = client.get("/api/screen?codes=005930")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)
        assert "meta" in body
        assert body["meta"]["market"] == "ALL"

    def test_screen_with_market_filter(self, mock_fetcher, mock_config):
        """마켓 필터로 스크리닝합니다."""
        app = create_app()
        app.dependency_overrides[get_fetcher] = lambda: mock_fetcher
        app.dependency_overrides[get_config] = lambda: mock_config

        with patch("src.api.routes.krx") as mock_krx:
            mock_krx.get_all_stocks.return_value = []
            c = TestClient(app)
            response = c.get("/api/screen?market=KOSPI")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["meta"]["market"] == "KOSPI"
        app.dependency_overrides.clear()

    def test_screen_empty_result(self, mock_fetcher, mock_config):
        """빈 결과를 반환합니다."""
        app = create_app()
        app.dependency_overrides[get_fetcher] = lambda: mock_fetcher
        app.dependency_overrides[get_config] = lambda: mock_config

        with patch("src.api.routes.krx") as mock_krx:
            mock_krx.get_all_stocks.return_value = []
            c = TestClient(app)
            response = c.get("/api/screen")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"] == []
        assert body["meta"]["total"] == 0
        app.dependency_overrides.clear()

    def test_screen_invalid_market(self):
        """잘못된 마켓 파라미터는 422를 반환합니다."""
        app = create_app()
        c = TestClient(app)
        response = c.get("/api/screen?market=INVALID")
        assert response.status_code == 422

    def test_screen_min_strength_filter(self, client):
        """min_strength 필터가 동작합니다."""
        response = client.get("/api/screen?codes=005930&min_strength=5")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        for item in body["data"]:
            assert item["signal_strength"] >= 5

    def test_screen_invalid_min_strength(self):
        """잘못된 min_strength는 422를 반환합니다."""
        app = create_app()
        c = TestClient(app)
        response = c.get("/api/screen?min_strength=0")
        assert response.status_code == 422

    def test_screen_invalid_days(self):
        """잘못된 days 파라미터는 422를 반환합니다."""
        app = create_app()
        c = TestClient(app)
        response = c.get("/api/screen?days=0")
        assert response.status_code == 422


class TestStockDetailEndpoint:
    """GET /api/stocks/{code} 테스트."""

    def test_get_stock_detail(self, client):
        """종목 상세 정보를 조회합니다."""
        response = client.get("/api/stocks/005930")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        data = body["data"]
        assert data["info"]["code"] == "005930"
        assert data["info"]["name"] == "삼성전자"
        assert "dmi" in data["indicators"]
        assert "stochastic" in data["indicators"]
        assert "chaikin" in data["indicators"]
        assert "macd" in data["indicators"]
        assert "demark" in data["indicators"]
        assert "signal_strength" in data["dream_team"]
        assert "signal_grade" in data["dream_team"]

    def test_get_stock_detail_not_found(self, mock_config):
        """존재하지 않는 종목은 404를 반환합니다."""
        failing_fetcher = MagicMock()
        failing_fetcher.get_stock_data.side_effect = Exception("종목 없음")

        app = create_app()
        app.dependency_overrides[get_fetcher] = lambda: failing_fetcher
        app.dependency_overrides[get_config] = lambda: mock_config
        c = TestClient(app)

        response = c.get("/api/stocks/999999")

        assert response.status_code == 404
        body = response.json()
        assert "detail" in body
        app.dependency_overrides.clear()

    def test_stock_detail_indicator_structure(self, client):
        """지표 응답 구조를 검증합니다."""
        response = client.get("/api/stocks/005930")
        body = response.json()
        indicators = body["data"]["indicators"]

        dmi = indicators["dmi"]
        assert "plus_di" in dmi
        assert "minus_di" in dmi
        assert "adx" in dmi
        assert "buy_signal" in dmi

        stoch = indicators["stochastic"]
        assert "k" in stoch
        assert "d" in stoch
        assert "buy_reinforcement" in stoch

        chaikin = indicators["chaikin"]
        assert "value" in chaikin
        assert "buy_signal" in chaikin

        macd = indicators["macd"]
        assert "macd" in macd
        assert "signal" in macd
        assert "oscillator" in macd
        assert "buy_signal" in macd

        demark = indicators["demark"]
        assert "setup_count" in demark
        assert "countdown_count" in demark
        assert "setup_complete" in demark


class TestIndicatorsEndpoint:
    """GET /api/indicators 테스트."""

    def test_get_indicator_config(self):
        """지표 설정을 조회합니다."""
        app = create_app()
        c = TestClient(app)
        response = c.get("/api/indicators")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        data = body["data"]

        assert data["dmi"]["period"] == 14
        assert data["stochastic"]["k_period"] == 14
        assert data["stochastic"]["d_period"] == 3
        assert data["stochastic"]["slowing"] == 3
        assert data["chaikin"]["fast_period"] == 3
        assert data["chaikin"]["slow_period"] == 10
        assert data["macd"]["fast"] == 12
        assert data["macd"]["slow"] == 26
        assert data["macd"]["signal"] == 9
        assert data["demark"]["lookback"] == 4
        assert data["screening"]["lookback_days"] == 5
        assert data["screening"]["default_days"] == 200


class TestErrorHandling:
    """에러 핸들링 테스트."""

    def test_screen_data_fetch_failure_skips(self, mock_config):
        """데이터 수집 실패 시 해당 종목을 건너뜁니다."""
        failing_fetcher = MagicMock()
        failing_fetcher.get_stock_data.side_effect = Exception("서버 오류")

        app = create_app()
        app.dependency_overrides[get_fetcher] = lambda: failing_fetcher
        app.dependency_overrides[get_config] = lambda: mock_config
        c = TestClient(app)

        response = c.get("/api/screen?codes=005930")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"] == []
        app.dependency_overrides.clear()

    def test_nonexistent_endpoint(self):
        """존재하지 않는 엔드포인트는 404를 반환합니다."""
        app = create_app()
        c = TestClient(app)
        response = c.get("/api/nonexistent")
        assert response.status_code == 404
