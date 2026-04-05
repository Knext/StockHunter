"""HTML 보고서 생성 모듈 테스트."""

from datetime import date
from pathlib import Path

import pytest

from src.batch.types import BatchResult
from src.report.generator import generate_report
from src.report.types import ReportConfig
from src.screener.types import DreamTeamSignal
from src.types.stock import StockInfo


def _make_signal(
    code: str,
    name: str,
    grade: str,
    strength: int,
    *,
    dmi: bool = True,
    stochastic: bool = False,
    chaikin: bool = False,
    macd: bool = False,
    demark: bool = False,
) -> DreamTeamSignal:
    return DreamTeamSignal(
        stock_info=StockInfo(
            code=code,
            name=name,
            market="KOSPI",
            sector="전기전자",
        ),
        date=date(2026, 4, 5),
        dmi_signal=dmi,
        stochastic_signal=stochastic,
        chaikin_signal=chaikin,
        macd_signal=macd,
        demark_signal=demark,
        signal_strength=strength,
        signal_grade=grade,
    )


def _make_batch_result(
    signals: tuple[DreamTeamSignal, ...] = (),
    failed_codes: tuple[str, ...] = (),
) -> BatchResult:
    return BatchResult(
        signals=signals,
        stock_data_map={},
        total_stocks=100,
        success_count=95,
        failed_codes=failed_codes,
        started_at="2026-04-05T09:00:00",
        finished_at="2026-04-05T09:30:00",
        market="KOSPI",
    )


class TestGenerateReport:
    """generate_report 함수 테스트."""

    def test_generates_html_file(self, tmp_path: Path) -> None:
        """보고서 HTML 파일이 생성되는지 확인한다."""
        signals = (
            _make_signal("005930", "삼성전자", "완전매수", 5, dmi=True, stochastic=True, chaikin=True, macd=True, demark=True),
            _make_signal("000660", "SK하이닉스", "이중매수", 4, dmi=True, stochastic=True, chaikin=True, macd=True),
        )
        batch = _make_batch_result(signals=signals)
        config = ReportConfig(output_dir=tmp_path)

        result_path = generate_report(batch, {}, config)

        assert result_path.exists()
        assert result_path.name == "report.html"

    def test_html_contains_required_text(self, tmp_path: Path) -> None:
        """생성된 HTML에 필수 텍스트가 포함되어 있는지 확인한다."""
        signals = (
            _make_signal("005930", "삼성전자", "완전매수", 5, dmi=True, stochastic=True, chaikin=True, macd=True, demark=True),
            _make_signal("035420", "NAVER", "기본매수", 2, dmi=True, stochastic=True),
        )
        batch = _make_batch_result(signals=signals)
        config = ReportConfig(output_dir=tmp_path)

        result_path = generate_report(batch, {}, config)
        html = result_path.read_text(encoding="utf-8")

        assert "드림팀 스크리닝 보고서" in html
        assert "완전매수" in html
        assert "기본매수" in html
        assert "삼성전자" in html
        assert "005930" in html
        assert "NAVER" in html
        assert "KOSPI" in html

    def test_empty_signals(self, tmp_path: Path) -> None:
        """신호가 없을 때 정상 동작하는지 확인한다."""
        batch = _make_batch_result(signals=())
        config = ReportConfig(output_dir=tmp_path)

        result_path = generate_report(batch, {}, config)

        assert result_path.exists()
        html = result_path.read_text(encoding="utf-8")
        assert "드림팀 스크리닝 보고서" in html
        assert "신호 0" in html

    def test_empty_chart_paths_shows_no_chart(self, tmp_path: Path) -> None:
        """차트 경로가 없을 때 '차트 없음'이 표시되는지 확인한다."""
        signals = (
            _make_signal("005930", "삼성전자", "완전매수", 5, dmi=True, stochastic=True, chaikin=True, macd=True, demark=True),
        )
        batch = _make_batch_result(signals=signals)
        config = ReportConfig(output_dir=tmp_path)

        result_path = generate_report(batch, {}, config)
        html = result_path.read_text(encoding="utf-8")

        assert "차트 없음" in html

    def test_chart_embed_base64(self, tmp_path: Path) -> None:
        """차트가 base64로 임베드되는지 확인한다."""
        chart_file = tmp_path / "005930.png"
        chart_file.write_bytes(b"\x89PNG\r\n\x1a\nfake_png_data")

        signals = (
            _make_signal("005930", "삼성전자", "완전매수", 5, dmi=True, stochastic=True, chaikin=True, macd=True, demark=True),
        )
        batch = _make_batch_result(signals=signals)
        config = ReportConfig(output_dir=tmp_path, embed_charts=True)

        result_path = generate_report(batch, {"005930": chart_file}, config)
        html = result_path.read_text(encoding="utf-8")

        assert "data:image/png;base64," in html
        assert "차트 없음" not in html

    def test_indicator_check_marks(self, tmp_path: Path) -> None:
        """지표 체크/미체크 마크가 올바르게 표시되는지 확인한다."""
        signals = (
            _make_signal(
                "005930", "삼성전자", "매수강화", 3,
                dmi=True, stochastic=True, chaikin=True, macd=False, demark=False,
            ),
        )
        batch = _make_batch_result(signals=signals)
        config = ReportConfig(output_dir=tmp_path)

        result_path = generate_report(batch, {}, config)
        html = result_path.read_text(encoding="utf-8")

        assert "강도 3/5" in html
        assert "매수강화" in html

    def test_appendix_contains_failed_codes(self, tmp_path: Path) -> None:
        """부록에 실패 종목 코드가 표시되는지 확인한다."""
        batch = _make_batch_result(
            signals=(),
            failed_codes=("999999", "888888"),
        )
        config = ReportConfig(output_dir=tmp_path)

        result_path = generate_report(batch, {}, config)
        html = result_path.read_text(encoding="utf-8")

        assert "999999" in html
        assert "888888" in html

    def test_grade_ordering(self, tmp_path: Path) -> None:
        """등급이 올바른 순서로 표시되는지 확인한다 (완전매수 먼저)."""
        signals = (
            _make_signal("000001", "종목A", "기본매수", 2, dmi=True, stochastic=True),
            _make_signal("000002", "종목B", "완전매수", 5, dmi=True, stochastic=True, chaikin=True, macd=True, demark=True),
        )
        batch = _make_batch_result(signals=signals)
        config = ReportConfig(output_dir=tmp_path)

        result_path = generate_report(batch, {}, config)
        html = result_path.read_text(encoding="utf-8")

        pos_full = html.index("완전매수 (1종목)")
        pos_basic = html.index("기본매수 (1종목)")
        assert pos_full < pos_basic

    def test_output_directory_structure(self, tmp_path: Path) -> None:
        """날짜별 디렉토리 구조가 올바르게 생성되는지 확인한다."""
        batch = _make_batch_result()
        config = ReportConfig(output_dir=tmp_path)

        result_path = generate_report(batch, {}, config)

        # 날짜 디렉토리가 YYYY-MM-DD 형식인지 확인
        date_dir = result_path.parent
        assert len(date_dir.name) == 10  # YYYY-MM-DD
        assert date_dir.name.count("-") == 2
