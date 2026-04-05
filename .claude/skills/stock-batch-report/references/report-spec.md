# 배치 보고서 사양

## 보고서 구조

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>드림팀 스크리닝 보고서 — {날짜}</title>
  <style>/* 인라인 CSS */</style>
</head>
<body>
  <!-- 1. 헤더 -->
  <header>
    <h1>드림팀 스크리닝 보고서</h1>
    <p>실행일시: {datetime} | 대상: {market} | 종목 수: {total}</p>
  </header>

  <!-- 2. 요약 대시보드 -->
  <section class="summary">
    <div class="stat-card">완전매수: {N}종목</div>
    <div class="stat-card">이중매수: {N}종목</div>
    <div class="stat-card">매수강화: {N}종목</div>
    <div class="stat-card">기본매수: {N}종목</div>
  </section>

  <!-- 3. 등급별 종목 카드 -->
  <section class="grade-section">
    <h2>🔴 완전매수 (신호강도 5)</h2>
    <div class="stock-card">
      <div class="stock-header">
        <span class="stock-name">{종목명}</span>
        <span class="stock-code">({종목코드})</span>
        <span class="grade-badge">완전매수</span>
      </div>
      <div class="indicators">
        <table>
          <tr>
            <th>DMI</th><th>스토캐스틱</th><th>채킨</th><th>MACD</th><th>드마크</th>
          </tr>
          <tr>
            <td class="active">✅</td>
            <td class="active">✅</td>
            <td class="active">✅</td>
            <td class="active">✅</td>
            <td class="active">✅</td>
          </tr>
        </table>
      </div>
      <div class="chart">
        <img src="data:image/png;base64,{base64_chart}" alt="{종목명} 차트">
      </div>
    </div>
    <!-- 반복 -->
  </section>

  <!-- 4. 부록 -->
  <section class="appendix">
    <h2>실행 정보</h2>
    <ul>
      <li>실행 시간: {elapsed}초</li>
      <li>스크리닝 대상: {total_stocks}종목</li>
      <li>데이터 수집 실패: {failed_count}종목</li>
    </ul>
  </section>
</body>
</html>
```

## 차트 사양

### 메인 차트 (캔들스틱)
- 최근 60 영업일 일봉
- 이동평균선: 5일(빨강), 20일(파랑), 60일(녹색)
- 거래량 바 (하단)
- 매수 신호일: 삼각형 마커 (▲ 빨강)

### 서브플롯
1. **DMI**: +DI(녹색), -DI(빨강), ADX(파랑), ADX=30 기준선(점선)
2. **스토캐스틱**: %K(파랑), %D(주황), 80선(점선), 20선(점선)
3. **채킨 오실레이터**: CO값(파랑), 0선(점선)
4. **MACD 오실레이터**: 오실레이터 히스토그램(녹색/빨강), MACD선(파랑), 시그널선(주황)

### 차트 스타일
- 배경: 흰색
- 그리드: 연한 회색
- 폰트: AppleGothic (macOS) / NanumGothic (Linux) / Malgun Gothic (Windows)
- DPI: 300
- 사이즈: 12x16 인치

## 배치 처리 사양

### 병렬 처리 구조
```
전체 종목 (~1700개)
  → 배치 분할 (50개씩)
  → asyncio.gather로 배치 단위 병렬 실행
    → 각 배치 내에서는 순차 처리 (레이트 리미팅)
  → 결과 수집 및 통합
```

### 병렬 제어
- `batch_size`: 50 (기본값)
- `max_concurrent_batches`: 3 (동시 배치 수, Semaphore)
- 배치 내 종목 간 대기: 0.5초 (rate_limit_seconds)
- 예상 실행 시간: ~1700종목 × 0.5초 / 3 = ~280초 (~5분)

### 배치 결과 타입
```python
@dataclass(frozen=True)
class BatchResult:
    signals: tuple[DreamTeamSignal, ...]  # 스크리닝 통과 종목
    stock_data_map: dict[str, StockData]  # 코드 → StockData (차트용)
    total_stocks: int                     # 전체 대상 종목 수
    success_count: int                    # 성공 종목 수
    failed_codes: tuple[str, ...]         # 실패 종목 코드
    started_at: str                       # 시작 시간 (ISO)
    finished_at: str                      # 종료 시간 (ISO)
    market: str                           # 대상 시장
```

## 파일 출력 구조

```
reports/
  └── {YYYY-MM-DD}/
      ├── report.html          # 최종 보고서
      └── charts/              # 개별 차트 이미지
          ├── 005930_삼성전자.png
          ├── 000660_SK하이닉스.png
          └── ...
```

## 스케줄링

- 실행 주기: 매주 금요일 12:00 PM KST
- Claude Code의 `schedule` 스킬 또는 `CronCreate` 도구 사용
- cron 표현식: `0 12 * * 5` (매주 금요일 12시)
- 실행 명령: `cd /Users/sean/ClaudeTest/StockHunter && python -m src.batch.runner`
