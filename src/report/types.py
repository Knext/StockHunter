from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReportConfig:
    """HTML 보고서 생성 설정.

    Attributes:
        output_dir: 보고서 출력 디렉토리
        embed_charts: 차트를 base64로 인라인 임베드할지 여부
        title: 보고서 제목
        min_strength: 리포트에 포함할 최소 순차 단계 (1-4).
            배치 파이프라인은 dream-index-config.yaml의 report.min_strength로
            이 값을 덮어쓴다. 독립 호출 시 기본값은 2(매수강화 이상)이다.
    """

    output_dir: Path = Path("reports")
    embed_charts: bool = True
    title: str = "드림팀 스크리닝 보고서"
    min_strength: int = 2
