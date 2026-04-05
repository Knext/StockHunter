"""HTML 보고서 생성 모듈."""

import base64
import logging
from datetime import datetime
from pathlib import Path

from src.batch.types import BatchResult
from src.report.templates import (
    CSS_STYLES,
    GRADE_BAR_ITEM_TEMPLATE,
    HTML_TEMPLATE,
    STOCK_CARD_TEMPLATE,
    SUMMARY_ROW_TEMPLATE,
)
from src.report.types import ReportConfig
from src.screener.types import DreamTeamSignal

logger = logging.getLogger(__name__)

GRADE_ORDER = ["완전매수", "이중매수", "매수강화", "기본매수"]
GRADE_COLORS = {
    "완전매수": "#D32F2F",
    "이중매수": "#FF9800",
    "매수강화": "#FFC107",
    "기본매수": "#4CAF50",
}


def _indicator_dot(active: bool) -> str:
    """지표 활성 여부를 dot HTML로 반환한다."""
    cls = "indicator-dot active" if active else "indicator-dot"
    return f'<span class="{cls}"></span>'


def _group_signals_by_grade(
    signals: tuple[DreamTeamSignal, ...],
) -> dict[str, list[DreamTeamSignal]]:
    """등급별로 신호를 그룹핑한다."""
    groups: dict[str, list[DreamTeamSignal]] = {
        grade: [] for grade in GRADE_ORDER
    }
    for signal in signals:
        grade = signal.signal_grade
        if grade in groups:
            groups[grade].append(signal)
        else:
            logger.warning("알 수 없는 등급: %s (종목: %s)", grade, signal.stock_info.code)
    return groups


def _build_grade_bar_html(grade_counts: dict[str, int]) -> str:
    """등급 바 HTML을 생성한다."""
    items: list[str] = []
    for grade in GRADE_ORDER:
        count = grade_counts.get(grade, 0)
        color = GRADE_COLORS.get(grade, "#999")
        items.append(GRADE_BAR_ITEM_TEMPLATE.format(
            grade=grade, count=count, color=color,
        ))
    return "\n".join(items)


def _build_summary_rows_html(signals: tuple[DreamTeamSignal, ...]) -> str:
    """요약 테이블 행 HTML을 생성한다."""
    rows: list[str] = []
    for sig in signals:
        info = sig.stock_info
        grade_color = GRADE_COLORS.get(sig.signal_grade, "#999")
        rows.append(SUMMARY_ROW_TEMPLATE.format(
            name=info.name,
            code=info.code,
            grade=sig.signal_grade,
            grade_color=grade_color,
            strength=sig.signal_strength,
            dmi=_indicator_dot(sig.dmi_signal),
            stochastic=_indicator_dot(sig.stochastic_signal),
            chaikin=_indicator_dot(sig.chaikin_signal),
            macd=_indicator_dot(sig.macd_signal),
            demark=_indicator_dot(sig.demark_signal),
        ))
    return "\n".join(rows)


def _build_chart_html(
    code: str,
    chart_paths: dict[str, Path],
    embed: bool,
) -> str:
    """차트 HTML을 생성한다."""
    chart_path = chart_paths.get(code)
    if chart_path is None or not Path(chart_path).exists():
        return '<p class="no-chart">차트 없음</p>'

    if embed:
        try:
            data = Path(chart_path).read_bytes()
            b64 = base64.b64encode(data).decode("ascii")
            return f'<img src="data:image/png;base64,{b64}" alt="{code} 차트">'
        except OSError:
            logger.exception("차트 파일 읽기 실패: %s", chart_path)
            return '<p class="no-chart">차트 없음</p>'

    return f'<img src="{chart_path}" alt="{code} 차트">'


def _build_stock_card(
    signal: DreamTeamSignal,
    chart_paths: dict[str, Path],
    embed: bool,
) -> str:
    """개별 종목 카드 HTML을 생성한다."""
    info = signal.stock_info
    grade_color = GRADE_COLORS.get(signal.signal_grade, "#999")
    return STOCK_CARD_TEMPLATE.format(
        name=info.name,
        code=info.code,
        market=info.market,
        sector=info.sector,
        grade=signal.signal_grade,
        grade_color=grade_color,
        strength=signal.signal_strength,
        chart_html=_build_chart_html(info.code, chart_paths, embed),
    )


def _build_sections_html(
    groups: dict[str, list[DreamTeamSignal]],
    chart_paths: dict[str, Path],
    embed: bool,
) -> str:
    """등급별 섹션 HTML을 생성한다."""
    sections: list[str] = []
    for grade in GRADE_ORDER:
        signals = groups.get(grade, [])
        if not signals:
            continue
        color = GRADE_COLORS.get(grade, "#999")
        cards = "\n".join(
            _build_stock_card(sig, chart_paths, embed) for sig in signals
        )
        sections.append(
            f'<div class="section">'
            f'<h2 style="color: {color};">{grade} ({len(signals)}종목)</h2>'
            f"{cards}"
            f"</div>"
        )
    return "\n".join(sections)


def _build_appendix_html(batch_result: BatchResult) -> str:
    """부록 HTML을 생성한다."""
    failed_list = ", ".join(batch_result.failed_codes) if batch_result.failed_codes else "없음"
    return (
        "<h2>부록 — 실행 정보</h2>"
        "<table>"
        "<tbody>"
        f"<tr><th>배치 시작</th><td>{batch_result.started_at}</td></tr>"
        f"<tr><th>배치 종료</th><td>{batch_result.finished_at}</td></tr>"
        f"<tr><th>대상 시장</th><td>{batch_result.market}</td></tr>"
        f"<tr><th>전체 대상 종목</th><td>{batch_result.total_stocks}</td></tr>"
        f"<tr><th>데이터 수집 성공</th><td>{batch_result.success_count}</td></tr>"
        f"<tr><th>데이터 수집 실패</th><td>{len(batch_result.failed_codes)}</td></tr>"
        f"<tr><th>신호 감지 종목</th><td>{len(batch_result.signals)}</td></tr>"
        f"<tr><th>실패 종목 코드</th><td>{failed_list}</td></tr>"
        "</tbody>"
        "</table>"
    )


def generate_report(
    batch_result: BatchResult,
    chart_paths: dict[str, Path],
    config: ReportConfig | None = None,
) -> Path:
    """배치 결과 + 차트를 종합하여 HTML 보고서를 생성한다."""
    if config is None:
        config = ReportConfig()

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    run_datetime = now.strftime("%Y-%m-%d %H:%M:%S")

    output_dir = config.output_dir / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "report.html"

    groups = _group_signals_by_grade(batch_result.signals)
    grade_counts = {grade: len(sigs) for grade, sigs in groups.items()}

    grade_bar_html = _build_grade_bar_html(grade_counts)
    summary_rows_html = _build_summary_rows_html(batch_result.signals)
    sections_html = _build_sections_html(groups, chart_paths, config.embed_charts)
    appendix_html = _build_appendix_html(batch_result)

    filter_options_parts: list[str] = []
    for grade in GRADE_ORDER:
        count = grade_counts.get(grade, 0)
        if count > 0:
            filter_options_parts.append(
                f'<option value="{grade}">{grade} ({count})</option>'
            )
    filter_options = "\n".join(filter_options_parts)

    html = HTML_TEMPLATE.format(
        title=config.title,
        css_styles=CSS_STYLES.format(),
        run_datetime=run_datetime,
        market=batch_result.market,
        total_stocks=batch_result.total_stocks,
        success_count=batch_result.success_count,
        signal_count=len(batch_result.signals),
        grade_bar_html=grade_bar_html,
        summary_rows_html=summary_rows_html,
        sections_html=sections_html,
        appendix_html=appendix_html,
        filter_options=filter_options,
    )

    output_path.write_text(html, encoding="utf-8")
    logger.info("보고서 생성 완료: %s", output_path)

    return output_path
