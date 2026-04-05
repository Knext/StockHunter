from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReportConfig:
    """HTML 보고서 생성 설정.

    Attributes:
        output_dir: 보고서 출력 디렉토리
        embed_charts: 차트를 base64로 인라인 임베드할지 여부
        title: 보고서 제목
    """

    output_dir: Path = Path("reports")
    embed_charts: bool = True
    title: str = "드림팀 스크리닝 보고서"
    min_strength: int = 2
