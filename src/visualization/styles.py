"""차트 스타일 및 색상 상수 모듈."""

import platform

import matplotlib


def setup_korean_font() -> None:
    """운영체제에 맞는 한글 폰트를 설정한다."""
    system = platform.system()
    if system == "Darwin":
        font_name = "AppleGothic"
    elif system == "Windows":
        font_name = "Malgun Gothic"
    else:
        font_name = "NanumGothic"
    matplotlib.rcParams["font.family"] = font_name
    matplotlib.rcParams["axes.unicode_minus"] = False


CHART_DPI = 100
CHART_WIDTH = 8  # inches
CHART_HEIGHT = 11  # inches
CANDLE_DAYS = 60

# 색상 상수
COLOR_UP = "#D32F2F"       # 상승 (빨강 — 한국식)
COLOR_DOWN = "#1976D2"     # 하락 (파랑)
COLOR_PLUS_DI = "#4CAF50"  # +DI
COLOR_MINUS_DI = "#F44336"  # -DI
COLOR_ADX = "#2196F3"      # ADX
COLOR_STOCH_K = "#2196F3"  # %K
COLOR_STOCH_D = "#FF9800"  # %D
COLOR_CHAIKIN = "#2196F3"
COLOR_MACD = "#2196F3"
COLOR_SIGNAL_LINE = "#FF9800"
COLOR_HIST_POS = "#4CAF50"
COLOR_HIST_NEG = "#F44336"
COLOR_MA5 = "#F44336"
COLOR_MA20 = "#2196F3"
COLOR_MA60 = "#4CAF50"
COLOR_BUY_MARKER = "#FF0000"
COLOR_GRID = "#E0E0E0"
COLOR_REFERENCE = "#9E9E9E"
MA_PERIODS = (5, 20, 60)
