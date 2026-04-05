---
name: stock-batch-report
description: "드림팀 주간 배치 스크리닝 보고서 시스템 구축. 전 종목 배치 처리, 차트 생성, HTML 보고서 생성. /stock-batch-report로 호출."
---

# StockHunter Batch Report Orchestrator

기존 드림팀 스크리닝 엔진을 활용하여 전 종목을 배치 처리하고, 차트와 함께 HTML 보고서를 생성하는 시스템을 구축하는 오케스트레이터.

## 실행 모드: 서브 에이전트

> **서브 에이전트 선택 근거:** 각 모듈(배치/차트/보고서)이 독립적 구현 작업이고, 워커 간 실시간 토론이 불필요한 데이터 파이프라인 구축. 매주 자동 실행되는 배치 작업이라 토큰 효율성 중요.

## 에이전트 구성

| 에이전트 | subagent_type | 역할 | 출력 |
|---------|--------------|------|------|
| batch-impl | batch-processor (커스텀) | 배치 처리 파이프라인 구현 | `src/batch/` |
| chart-impl | chart-generator (커스텀) | 차트 생성 모듈 구현 | `src/visualization/` |
| report-impl | report-builder (커스텀) | HTML 보고서 생성기 구현 | `src/report/` |

## 사전 조건

이 스킬은 기존 StockHunter 프로젝트가 완성된 상태에서 실행한다:
- `src/data/krx.py` — KRX 데이터 수집
- `src/data/cache.py` — 캐싱 레이어
- `src/indicators/` — 5개 지표 계산기
- `src/screener/engine.py` — 드림팀 스크리닝 엔진
- `src/types/` — 데이터 모델

## 워크플로우

### Phase 1: 준비

1. 기존 프로젝트 상태 확인:
   - `src/screener/engine.py`의 `screen_stock()`, `screen_all()` 함수 존재 확인
   - `src/data/krx.py`의 `get_all_stocks()`, `get_daily_ohlcv()` 함수 존재 확인
   - `src/types/` 데이터 모델 확인
2. `_workspace/` 디렉토리 생성 (없으면)
3. `references/report-spec.md`를 Read하여 상세 사양 확인

### Phase 2: 배치 처리 모듈 구현

**실행 방식:** 순차 (이 모듈이 차트/보고서의 입력을 제공)

Agent 호출:
```
Agent(
  name: "batch-impl",
  subagent_type: "batch-processor",
  prompt: "StockHunter 프로젝트에 배치 스크리닝 파이프라인을 구현하세요.

프로젝트 위치: /Users/sean/ClaudeTest/StockHunter

기존 모듈:
- src/data/krx.py: get_all_stocks(market), get_daily_ohlcv(code, start, end)
- src/data/cache.py: CachedDataFetcher (24시간 TTL JSON 캐시)
- src/screener/engine.py: screen_stock(stock_data, **params), screen_all(stocks, **params)
- src/types/ohlcv.py: OHLCV, StockData (frozen dataclass)
- src/types/stock.py: StockInfo (frozen dataclass)
- src/screener/types.py: DreamTeamSignal (frozen dataclass)
- src/config.py: Config (cache_dir, cache_ttl_hours, rate_limit_seconds)

구현할 파일:
1. src/batch/__init__.py
2. src/batch/types.py — BatchResult 타입 (frozen dataclass)
   - signals: tuple[DreamTeamSignal, ...] — 스크리닝 통과 종목
   - stock_data_map: dict[str, StockData] — 코드 → StockData (차트 생성용)
   - total_stocks: int, success_count: int, failed_codes: tuple[str, ...]
   - started_at: str, finished_at: str, market: str
3. src/batch/runner.py — 배치 실행기
   - run_batch(market, batch_size=50, max_concurrent=3) → BatchResult
   - asyncio 기반 병렬 처리: 전 종목을 batch_size개씩 분할
   - asyncio.Semaphore로 동시 배치 수 제한
   - 배치 내에서는 순차 처리 (레이트 리미팅)
   - __main__ 블록: python -m src.batch.runner로 실행 가능
4. tests/test_batch.py — 단위 테스트

원칙:
- 기존 모듈 재사용 (krx, screener, cache)
- 불변 패턴 (frozen dataclass)
- 부분 실패 허용 (개별 종목 실패 시 스킵)
- logging 모듈로 진행률 로깅
- 환경변수: BATCH_SIZE (기본 50), MAX_CONCURRENT (기본 3)

references/report-spec.md의 '배치 처리 사양' 섹션을 Read하여 상세 사양을 확인하세요."
)
```

**산출물:** `src/batch/runner.py`, `src/batch/types.py`, `tests/test_batch.py`

### Phase 3: 차트 + 보고서 모듈 구현 (병렬)

**실행 방식:** 병렬 (두 모듈이 독립적)

단일 메시지에서 2개 Agent를 동시 호출:

#### 3-1. 차트 생성 모듈

```
Agent(
  name: "chart-impl",
  subagent_type: "chart-generator",
  run_in_background: true,
  prompt: "StockHunter 프로젝트에 차트 생성 모듈을 구현하세요.

프로젝트 위치: /Users/sean/ClaudeTest/StockHunter

기존 모듈:
- src/types/ohlcv.py: OHLCV(date, open, high, low, close, volume), StockData(info, daily, weekly)
- src/indicators/dmi.py: calculate_dmi() → tuple[DMIResult, ...]
- src/indicators/stochastic.py: calculate_stochastic() → tuple[StochasticResult, ...]
- src/indicators/chaikin.py: calculate_chaikin() → tuple[ChaikinResult, ...]
- src/indicators/macd.py: calculate_macd_oscillator() → tuple[MACDOscResult, ...]
- src/indicators/demark.py: calculate_demark() → tuple[DeMarkResult, ...]
- src/screener/types.py: DreamTeamSignal(stock_info, date, dmi_signal, stochastic_signal, chaikin_signal, macd_signal, demark_signal, signal_strength, signal_grade)

구현할 파일:
1. src/visualization/__init__.py
2. src/visualization/styles.py — 차트 스타일/컬러 상수, 한글 폰트 설정
   - 한글 폰트: AppleGothic(macOS) / NanumGothic(Linux) / Malgun Gothic(Windows)
   - 차트 색상, DPI, 사이즈 등 상수
3. src/visualization/chart.py — 차트 생성기
   - generate_stock_chart(stock_data: StockData, signal: DreamTeamSignal, output_dir: Path) → Path
     - 메인 차트: 캔들스틱 (최근 60 영업일) + 거래량 + MA(5,20,60)
     - 서브플롯 1: DMI (+DI 녹색, -DI 빨강, ADX 파랑, 30선 점선)
     - 서브플롯 2: 스토캐스틱 (%K 파랑, %D 주황, 80/20선 점선)
     - 서브플롯 3: 채킨 오실레이터 (CO값 파랑, 0선 점선)
     - 서브플롯 4: MACD 오실레이터 (히스토그램 녹/빨, MACD 파랑, Signal 주황)
     - 매수 신호일: ▲ 빨강 마커
   - generate_all_charts(signals, stock_data_map, output_dir) → dict[str, Path]
     - 코드 → 차트 파일 경로 딕셔너리 반환
   - matplotlib 사용 (mplfinance 사용 가능하면 활용)
   - 이미지: 300 DPI, 12x16 인치
   - 파일명: {종목코드}_{종목명}.png
4. tests/test_chart.py — 단위 테스트 (mock 데이터로 차트 생성 검증)

pyproject.toml에 matplotlib 의존성 추가.
references/report-spec.md의 '차트 사양' 섹션을 Read하여 상세 사양을 확인하세요."
)
```

#### 3-2. 보고서 생성 모듈

```
Agent(
  name: "report-impl",
  subagent_type: "report-builder",
  run_in_background: true,
  prompt: "StockHunter 프로젝트에 HTML 보고서 생성 모듈을 구현하세요.

프로젝트 위치: /Users/sean/ClaudeTest/StockHunter

기존 모듈:
- src/screener/types.py: DreamTeamSignal 타입
- src/batch/types.py: BatchResult 타입 (Phase 2에서 생성됨)
  - signals, stock_data_map, total_stocks, success_count, failed_codes, started_at, finished_at, market

구현할 파일:
1. src/report/__init__.py
2. src/report/types.py — 보고서 설정 타입
   - ReportConfig(output_dir, embed_charts, title 등)
3. src/report/templates.py — HTML/CSS 템플릿
   - HTML_TEMPLATE: 전체 보고서 레이아웃
   - CSS_STYLES: 반응형 CSS
   - STOCK_CARD_TEMPLATE: 개별 종목 카드
   - INDICATOR_TABLE: 지표 체크 테이블
4. src/report/generator.py — 보고서 생성기
   - generate_report(batch_result: BatchResult, chart_paths: dict[str, Path], config: ReportConfig) → Path
     - BatchResult에서 등급별(완전매수→기본매수) 종목 분류
     - 각 종목에 대해 STOCK_CARD 생성 (지표 체크 테이블 + 차트)
     - 차트 이미지를 base64로 인라인 임베딩 (단일 HTML 파일)
     - 요약 대시보드 (등급별 종목 수)
     - 부록 (실행 정보, 실패 종목)
   - 출력: reports/{YYYY-MM-DD}/report.html
5. tests/test_report.py — 단위 테스트

보고서 디자인:
- 자체 완결적 HTML (외부 CDN 의존 없음)
- CSS는 <style> 태그 내 인라인
- 반응형 레이아웃 (모바일 가독성)
- 등급별 색상 구분: 완전매수(빨강), 이중매수(주황), 매수강화(노랑), 기본매수(초록)
- 지표 체크: ✅(활성) / ⬜(비활성)

references/report-spec.md의 '보고서 구조' 섹션을 Read하여 상세 사양을 확인하세요."
)
```

**산출물:**
- chart-impl: `src/visualization/chart.py`, `src/visualization/styles.py`
- report-impl: `src/report/generator.py`, `src/report/templates.py`, `src/report/types.py`

### Phase 4: 통합 및 엔트리포인트

Phase 2, 3의 산출물을 Read하여 확인한 후, 직접 통합 코드를 작성한다.

1. **`src/batch/runner.py` 업데이트** — 배치 실행 후 차트 생성 + 보고서 생성을 연결:
   ```python
   async def run_full_pipeline(market="ALL", batch_size=50, max_concurrent=3):
       # 1. 배치 스크리닝
       batch_result = await run_batch(market, batch_size, max_concurrent)
       
       # 2. 차트 생성
       output_dir = Path(f"reports/{date.today().isoformat()}")
       chart_dir = output_dir / "charts"
       chart_paths = generate_all_charts(
           batch_result.signals, batch_result.stock_data_map, chart_dir
       )
       
       # 3. 보고서 생성
       report_path = generate_report(
           batch_result, chart_paths, ReportConfig(output_dir=output_dir)
       )
       
       return report_path
   ```

2. **`src/batch/__main__.py`** — CLI 엔트리포인트:
   ```python
   # python -m src.batch 로 실행
   import asyncio
   from src.batch.runner import run_full_pipeline
   
   if __name__ == "__main__":
       report_path = asyncio.run(run_full_pipeline())
       print(f"보고서 생성 완료: {report_path}")
   ```

3. **`pyproject.toml` 업데이트** — 새 의존성 추가:
   - matplotlib >= 3.7
   - mplfinance >= 0.12 (선택)

4. **통합 테스트** 실행:
   ```bash
   cd /Users/sean/ClaudeTest/StockHunter
   python -m pytest tests/ -v
   ```

### Phase 5: 스케줄 설정

Claude Code의 `schedule` 기능으로 매주 금요일 12:00 PM 배치 실행을 예약한다.

```
CronCreate(
  schedule: "0 12 * * 5",
  description: "드림팀 주간 배치 스크리닝 보고서",
  command: "cd /Users/sean/ClaudeTest/StockHunter && python -m src.batch"
)
```

또는 사용자에게 다음 옵션을 제안:
1. **Claude Code schedule** — `CronCreate`로 자동 실행
2. **시스템 crontab** — `crontab -e`로 직접 등록
3. **launchd** (macOS) — `~/Library/LaunchAgents/`에 plist 생성

### Phase 6: 검증 및 정리

1. 생성된 모듈 구조 확인:
   ```
   src/
   ├── batch/
   │   ├── __init__.py
   │   ├── __main__.py
   │   ├── types.py
   │   └── runner.py
   ├── visualization/
   │   ├── __init__.py
   │   ├── styles.py
   │   └── chart.py
   └── report/
       ├── __init__.py
       ├── types.py
       ├── templates.py
       └── generator.py
   ```

2. 테스트 실행:
   ```bash
   python -m pytest tests/test_batch.py tests/test_chart.py tests/test_report.py -v
   ```

3. 드라이런 (소규모 테스트):
   ```bash
   BATCH_SIZE=5 MAX_CONCURRENT=1 python -m src.batch
   ```

4. `_workspace/` 보존

5. 사용자에게 결과 요약:
   - 생성된 모듈 목록
   - 실행 방법 (`python -m src.batch`)
   - 스케줄 설정 상태
   - 보고서 출력 경로 (`reports/{YYYY-MM-DD}/report.html`)

## 데이터 흐름

```
[Phase 2: batch-impl]
    └── src/batch/runner.py (run_batch)
           ├── krx.get_all_stocks() → 종목 목록
           ├── 50개씩 분할 → asyncio.gather
           ├── 각 배치: get_daily_ohlcv() → screen_stock()
           └── BatchResult 반환

[Phase 3-1: chart-impl]     [Phase 3-2: report-impl]
    └── src/visualization/       └── src/report/
        chart.py                     generator.py
        (StockData → PNG)            (BatchResult + charts → HTML)

[Phase 4: 통합]
    └── src/batch/runner.py (run_full_pipeline)
           ├── run_batch() → BatchResult
           ├── generate_all_charts() → chart_paths
           └── generate_report() → report.html

[Phase 5: 스케줄]
    └── 매주 금요일 12:00 PM → python -m src.batch
```

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| batch-impl 실패 | 1회 재시도. 재실패 시 사용자에게 알림 (핵심 모듈) |
| chart-impl 실패 | 차트 없이 텍스트 기반 보고서 생성으로 폴백 |
| report-impl 실패 | 1회 재시도. 재실패 시 JSON 결과만 출력 |
| 통합 시 인터페이스 불일치 | 에러 메시지 분석 후 해당 모듈 수정 |
| 배치 실행 중 API 장애 | 캐시 데이터 활용, 부분 결과로 보고서 생성 |

## 테스트 시나리오

### 정상 흐름
1. `/stock-batch-report` 호출
2. Phase 1: 기존 프로젝트 상태 확인 완료
3. Phase 2: batch-impl이 `src/batch/` 구현 → 테스트 통과
4. Phase 3: chart-impl + report-impl 병렬 실행 → 각각 테스트 통과
5. Phase 4: 통합 엔트리포인트 작성, 드라이런(5종목) 성공
6. Phase 5: 스케줄 설정 완료
7. 결과: `reports/{날짜}/report.html` 생성 확인

### 에러 흐름
1. Phase 3에서 chart-impl이 matplotlib 폰트 에러로 실패
2. 1회 재시도 (한글 폰트 설정 수정 프롬프트 추가)
3. 재시도 성공 시 정상 진행
4. 재실패 시 report-impl에 "차트 미포함" 옵션으로 진행
5. 최종 보고서에 "차트 생성 실패 — 텍스트 모드" 명시
