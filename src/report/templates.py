"""HTML 보고서 템플릿 및 CSS 스타일 — Figma Design System."""

INDICATOR_NAMES: list[str] = ["DMI", "스토캐스틱", "채킨", "MACD", "드마크"]

CSS_STYLES = """
:root {{
    --color-black: #000000;
    --color-white: #ffffff;
    --glass-dark: rgba(0, 0, 0, 0.08);
    --text-muted: rgba(0, 0, 0, 0.5);
    --border-color: rgba(0, 0, 0, 0.12);
    --border-subtle: rgba(0, 0, 0, 0.06);
    --font-sans: system-ui, -apple-system, 'Segoe UI', 'SF Pro Display', Helvetica, Arial, sans-serif;
    --font-mono: 'SF Mono', Menlo, monospace;
    --grade-full: #D32F2F;
    --grade-double: #FF9800;
    --grade-reinforced: #FFC107;
    --grade-basic: #4CAF50;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    background: var(--color-white);
    color: var(--color-black);
    font-family: var(--font-sans);
    font-size: 16px;
    font-weight: 340;
    line-height: 1.45;
    letter-spacing: -0.14px;
    font-feature-settings: "kern" 1;
    -webkit-font-smoothing: antialiased;
    overflow: hidden;
    height: 100vh;
}}

/* ── HERO ── */
.hero {{
    background: linear-gradient(135deg, #0acf83 0%, #a259ff 30%, #f24e1e 50%, #ff7262 65%, #1abcfe 80%, #0acf83 100%);
    padding: 32px 40px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;
}}

.hero-left h1 {{
    font-size: 28px;
    font-weight: 400;
    line-height: 1.0;
    letter-spacing: -0.56px;
    color: var(--color-white);
    margin-bottom: 6px;
}}

.hero-left .subtitle {{
    font-size: 14px;
    font-weight: 320;
    letter-spacing: -0.14px;
    color: rgba(255, 255, 255, 0.75);
}}

.hero-right {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}}

.hero-stat {{
    background: rgba(255, 255, 255, 0.16);
    backdrop-filter: blur(8px);
    padding: 6px 16px 8px;
    border-radius: 50px;
    font-size: 13px;
    font-weight: 480;
    letter-spacing: -0.14px;
    color: var(--color-white);
}}

/* ── GRADE BAR ── */
.grade-bar {{
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--border-color);
    background: var(--color-white);
}}

.grade-bar-item {{
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 14px 16px;
    border-right: 1px solid var(--border-subtle);
}}

.grade-bar-item:last-child {{
    border-right: none;
}}

.grade-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}}

.grade-bar-label {{
    font-family: var(--font-mono);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-muted);
}}

.grade-bar-count {{
    font-size: 20px;
    font-weight: 400;
    letter-spacing: -0.4px;
}}

/* ── MAIN LAYOUT ── */
.main-layout {{
    display: flex;
    height: calc(100vh - 130px);
    overflow: hidden;
}}

/* ── LEFT PANEL ── */
.left-panel {{
    width: 420px;
    min-width: 420px;
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    background: var(--color-white);
}}

.left-panel-header {{
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-shrink: 0;
}}

.left-panel-header .panel-title {{
    font-family: var(--font-mono);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-muted);
    white-space: nowrap;
}}

.left-panel-header select {{
    padding: 6px 14px 7px;
    border: 1px solid var(--border-color);
    border-radius: 50px;
    font-size: 13px;
    font-family: var(--font-sans);
    font-weight: 480;
    letter-spacing: -0.14px;
    background: var(--color-white);
    color: var(--color-black);
    cursor: pointer;
    -webkit-appearance: none;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L5 5L9 1' stroke='%23000' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 10px center;
    padding-right: 28px;
}}

.left-panel-header select:focus {{
    outline: 2px dashed var(--color-black);
    outline-offset: 3px;
}}

.left-scroll {{
    overflow-y: auto;
    flex: 1;
}}

/* ── SUMMARY TABLE (LEFT) ── */
.summary-table {{
    width: 100%;
    border-collapse: collapse;
}}

.summary-table thead {{
    position: sticky;
    top: 0;
    z-index: 10;
}}

.summary-table thead th {{
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-muted);
    padding: 10px 10px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
    background: var(--color-white);
    white-space: nowrap;
}}

.summary-table thead th.center {{
    text-align: center;
}}

.summary-table tbody tr {{
    border-bottom: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: background 0.12s;
}}

.summary-table tbody tr:hover {{
    background: var(--glass-dark);
}}

.summary-table tbody tr.selected {{
    background: rgba(0, 0, 0, 0.05);
    box-shadow: inset 3px 0 0 var(--color-black);
}}

.summary-table td {{
    padding: 8px 10px;
    font-size: 13px;
    font-weight: 340;
    letter-spacing: -0.14px;
    vertical-align: middle;
}}

.summary-table td.center {{
    text-align: center;
}}

.summary-table .stock-name-cell {{
    font-weight: 700;
    font-size: 13px;
    letter-spacing: normal;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 120px;
}}

.summary-table .code-cell {{
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.6px;
    color: var(--text-muted);
}}

.summary-table .grade-pill {{
    display: inline-block;
    padding: 2px 10px 3px;
    border-radius: 50px;
    font-size: 11px;
    font-weight: 480;
    color: var(--color-white);
    letter-spacing: -0.14px;
    white-space: nowrap;
}}

.indicator-dot {{
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--border-subtle);
}}

.indicator-dot.active {{
    background: var(--color-black);
}}

/* ── RIGHT PANEL ── */
.right-panel {{
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
}}

.right-panel-header {{
    padding: 16px 24px;
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    gap: 16px;
    flex-shrink: 0;
}}

.right-panel-header .panel-title {{
    font-family: var(--font-mono);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-muted);
}}

.right-panel-header .result-count {{
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.6px;
    color: var(--text-muted);
    margin-left: auto;
}}

.right-scroll {{
    overflow-y: auto;
    flex: 1;
    padding: 24px;
}}

/* ── STOCK CARDS (RIGHT) ── */
.section {{
    margin-bottom: 32px;
}}

.section h2 {{
    font-size: 22px;
    font-weight: 540;
    line-height: 1.35;
    letter-spacing: -0.26px;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border-subtle);
}}

.stock-card {{
    background: var(--color-white);
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 20px;
    border: 1px solid var(--border-color);
    border-left: 3px solid var(--border-color);
}}

.stock-card.grade-완전매수 {{ border-left-color: var(--grade-full); }}
.stock-card.grade-이중매수 {{ border-left-color: var(--grade-double); }}
.stock-card.grade-매수강화 {{ border-left-color: var(--grade-reinforced); }}
.stock-card.grade-기본매수 {{ border-left-color: var(--grade-basic); }}

.stock-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
    flex-wrap: wrap;
    gap: 10px;
}}

.stock-header .stock-name {{
    font-size: 20px;
    font-weight: 700;
    line-height: 1.45;
    letter-spacing: normal;
}}

.stock-header .stock-meta {{
    font-family: var(--font-mono);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-muted);
}}

.stock-header .badge {{
    display: inline-block;
    padding: 6px 16px 7px;
    border-radius: 50px;
    font-size: 13px;
    font-weight: 480;
    letter-spacing: -0.14px;
    color: var(--color-white);
}}

.chart-container {{
    text-align: center;
    margin-top: 12px;
}}

.chart-container img {{
    width: 100%;
    height: auto;
    border-radius: 8px;
    border: 1px solid var(--border-subtle);
}}

.no-chart {{
    color: var(--text-muted);
    font-size: 14px;
    font-weight: 340;
    padding: 32px;
    text-align: center;
    background: var(--glass-dark);
    border-radius: 8px;
}}

/* ── INDEX SECTION ── */
.index-section {{
    margin-bottom: 24px;
}}

.index-section .section-label {{
    font-family: var(--font-mono);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-muted);
    margin-bottom: 16px;
}}

.index-cards {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
}}

.index-card {{
    background: var(--color-white);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 20px;
}}

.index-header {{
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 8px;
    flex-wrap: wrap;
}}

.index-name {{
    font-size: 18px;
    font-weight: 700;
    letter-spacing: normal;
}}

.index-price {{
    font-size: 22px;
    font-weight: 400;
    letter-spacing: -0.44px;
}}

.index-card .chart-container img {{
    width: 100%;
    max-width: none;
}}

/* ── INDEX TOGGLE ── */
.index-toggle {{
    display: flex;
    gap: 16px;
    padding: 12px 20px;
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
}}

.index-toggle label {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    font-weight: 480;
    letter-spacing: -0.14px;
    cursor: pointer;
    user-select: none;
}}

.index-toggle input[type="checkbox"] {{
    width: 16px;
    height: 16px;
    accent-color: var(--color-black);
    cursor: pointer;
}}

/* ── APPENDIX ── */
.appendix {{
    background: var(--glass-dark);
    border-radius: 8px;
    padding: 24px;
    margin-top: 16px;
}}

.appendix h2 {{
    font-size: 18px;
    font-weight: 540;
    letter-spacing: -0.26px;
    margin-bottom: 16px;
}}

.appendix table {{
    width: 100%;
    border-collapse: collapse;
}}

.appendix th, .appendix td {{
    padding: 10px 14px;
    border-bottom: 1px solid var(--border-subtle);
    text-align: left;
    font-size: 13px;
    font-weight: 340;
    letter-spacing: -0.14px;
}}

.appendix th {{
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border-color);
}}

/* ── RESPONSIVE ── */
@media (max-width: 960px) {{
    body {{ overflow: auto; height: auto; }}
    .main-layout {{ flex-direction: column; height: auto; }}
    .left-panel {{ width: 100%; min-width: 0; border-right: none; border-bottom: 1px solid var(--border-color); max-height: 50vh; }}
    .right-panel {{ height: auto; }}
    .right-scroll {{ overflow-y: visible; }}
    .hero {{ flex-direction: column; text-align: center; }}
}}

/* ── PRINT ── */
@media print {{
    body {{ overflow: auto; height: auto; }}
    .main-layout {{ flex-direction: column; height: auto; }}
    .left-panel {{ width: 100%; min-width: 0; max-height: none; border-right: none; }}
    .right-scroll {{ overflow: visible; }}
    .hero {{ background: var(--color-black) !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .stock-card {{ break-inside: avoid; }}
}}
"""

GRADE_BAR_ITEM_TEMPLATE = (
    '<div class="grade-bar-item">'
    '<div class="grade-dot" style="background: {color};"></div>'
    '<span class="grade-bar-label">{grade}</span>'
    '<span class="grade-bar-count" style="color: {color};">{count}</span>'
    '</div>'
)

SUMMARY_ROW_TEMPLATE = (
    '<tr data-code="{code}" data-grade="{grade}">'
    '<td class="stock-name-cell">{name}</td>'
    '<td class="code-cell">{code}</td>'
    '<td><span class="grade-pill" style="background:{grade_color};">{grade}</span></td>'
    '<td class="center">{strength}</td>'
    '<td class="center">{dmi}</td>'
    '<td class="center">{stochastic}</td>'
    '<td class="center">{chaikin}</td>'
    '<td class="center">{macd}</td>'
    '<td class="center">{demark}</td>'
    '</tr>'
)

STOCK_CARD_TEMPLATE = """
<div class="stock-card grade-{grade}" data-grade="{grade}" data-code="{code}" id="card-{code}">
    <div class="stock-header">
        <span class="stock-name">{name} ({code})</span>
        <span class="stock-meta">{market} · {sector}</span>
        <span class="badge" style="background: {grade_color};">{grade} (강도 {strength}/5)</span>
    </div>
    <div class="chart-container">
        {chart_html}
    </div>
</div>
"""

FILTER_SCRIPT = """
<script>
(function() {{
    var gradeSelect = document.getElementById('gradeFilter');
    var countEl = document.getElementById('resultCount');
    var rows = document.querySelectorAll('.summary-table tbody tr');
    var rightScroll = document.querySelector('.right-scroll');

    function applyFilter() {{
        var gradeVal = gradeSelect.value;

        /* left panel rows */
        rows.forEach(function(row) {{
            var grade = row.getAttribute('data-grade');
            row.style.display = (gradeVal === 'all' || grade === gradeVal) ? '' : 'none';
        }});

        /* right panel cards */
        var sections = document.querySelectorAll('.section');
        var visibleCount = 0;

        sections.forEach(function(sec) {{
            var cards = sec.querySelectorAll('.stock-card');
            var sectionVisible = 0;

            cards.forEach(function(card) {{
                var grade = card.getAttribute('data-grade');
                if (gradeVal === 'all' || grade === gradeVal) {{
                    card.style.display = '';
                    sectionVisible++;
                    visibleCount++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});

            sec.style.display = sectionVisible === 0 ? 'none' : '';
        }});

        countEl.textContent = visibleCount + '종목';
    }}

    gradeSelect.addEventListener('change', applyFilter);

    /* index toggle */
    var toggleKospi = document.getElementById('toggleKospi');
    var toggleKosdaq = document.getElementById('toggleKosdaq');

    function applyIndexToggle() {{
        var kospiCards = document.querySelectorAll('[data-index="KS11"]');
        var kosdaqCards = document.querySelectorAll('[data-index="KQ11"]');
        kospiCards.forEach(function(c) {{ c.style.display = toggleKospi.checked ? '' : 'none'; }});
        kosdaqCards.forEach(function(c) {{ c.style.display = toggleKosdaq.checked ? '' : 'none'; }});

        var indexSection = document.getElementById('indexSection');
        if (indexSection) {{
            var anyVisible = toggleKospi.checked || toggleKosdaq.checked;
            indexSection.style.display = anyVisible ? '' : 'none';
        }}
    }}

    if (toggleKospi) toggleKospi.addEventListener('change', applyIndexToggle);
    if (toggleKosdaq) toggleKosdaq.addEventListener('change', applyIndexToggle);
    applyIndexToggle();

    /* row click → scroll right panel to card */
    rows.forEach(function(row) {{
        row.addEventListener('click', function() {{
            var code = row.getAttribute('data-code');
            var card = document.getElementById('card-' + code);
            if (!card) return;

            /* highlight selected row */
            rows.forEach(function(r) {{ r.classList.remove('selected'); }});
            row.classList.add('selected');

            /* scroll right panel */
            card.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }});
    }});

    applyFilter();
}})();
</script>
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{css_styles}
    </style>
</head>
<body>

    <div class="hero">
        <div class="hero-left">
            <h1>{title}</h1>
            <p class="subtitle">{run_datetime} · {market}</p>
        </div>
        <div class="hero-right">
            <span class="hero-stat">대상 {total_stocks}</span>
            <span class="hero-stat">성공 {success_count}</span>
            <span class="hero-stat">신호 {signal_count}</span>
        </div>
    </div>

    <div class="grade-bar">
        {grade_bar_html}
    </div>

    <div class="main-layout">

        <div class="left-panel">
            <div class="left-panel-header">
                <span class="panel-title">Signal Overview</span>
                <select id="gradeFilter">
                    <option value="all">전체 ({signal_count})</option>
                    {filter_options}
                </select>
            </div>
            <div class="left-scroll">
                <table class="summary-table">
                    <thead>
                        <tr>
                            <th>종목명</th>
                            <th>코드</th>
                            <th>등급</th>
                            <th class="center">강도</th>
                            <th class="center">DMI</th>
                            <th class="center">STO</th>
                            <th class="center">CHK</th>
                            <th class="center">MCD</th>
                            <th class="center">DMK</th>
                        </tr>
                    </thead>
                    <tbody>
                        {summary_rows_html}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="right-panel">
            <div class="right-panel-header">
                <span class="panel-title">Detail Charts</span>
                <div class="index-toggle">
                    <label><input type="checkbox" id="toggleKospi" checked> 코스피</label>
                    <label><input type="checkbox" id="toggleKosdaq" checked> 코스닥</label>
                </div>
                <span class="result-count" id="resultCount"></span>
            </div>
            <div class="right-scroll">
                <div class="index-section" id="indexSection">
                    <div class="index-cards">
                        {index_html}
                    </div>
                </div>

                {sections_html}

                <div class="appendix">
                    {appendix_html}
                </div>
            </div>
        </div>

    </div>
""" + FILTER_SCRIPT + """
</body>
</html>
"""
