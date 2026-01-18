import httpx

from app.config import settings
from app.schemas import PanelScenario


class LLMService:
    """Gemini LLM을 사용한 회의록 분석 서비스"""

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def analyze_meeting(self, meeting_text: str) -> list[PanelScenario]:
        """회의록을 분석하여 4컷 만화 시나리오 생성"""
        # TODO: Gemini API 연동 구현
        raise NotImplementedError("Gemini API 연동 구현 필요")


llm_service = LLMService()
