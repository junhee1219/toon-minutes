from google import genai
from google.genai import types

from app.config import settings
from app.schemas import PanelScenario


SYSTEM_PROMPT = """당신은 회의록을 4컷 만화 시나리오로 변환하는 전문가입니다.

회의록을 분석하여 핵심 내용을 4컷 만화로 표현할 수 있는 시나리오를 만들어주세요.
각 컷은 회의의 주요 포인트를 유머러스하거나 인상적으로 표현해야 합니다.

image_prompt 작성 규칙:
- 영어로 작성
- 만화/일러스트 스타일 명시
- 캐릭터, 배경, 행동을 구체적으로 설명
- 예: "cartoon style, office meeting room, a man presenting charts enthusiastically, colleagues looking surprised"
"""

# 4컷 만화 시나리오 스키마
PANELS_SCHEMA = types.Schema(
    type=types.Type.ARRAY,
    items=types.Schema(
        type=types.Type.OBJECT,
        required=["panel_number", "description", "image_prompt"],
        properties={
            "panel_number": types.Schema(type=types.Type.INTEGER),
            "description": types.Schema(type=types.Type.STRING),
            "dialogue": types.Schema(type=types.Type.STRING),
            "image_prompt": types.Schema(type=types.Type.STRING),
        },
    ),
)


class LLMService:
    """Gemini LLM을 사용한 회의록 분석 서비스"""

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-3-flash-preview"

    async def analyze_meeting(self, meeting_text: str) -> list[PanelScenario]:
        """회의록을 분석하여 4컷 만화 시나리오 생성"""
        prompt = f"""다음 회의록을 4컷 만화 시나리오로 변환해주세요.
정확히 4개의 패널을 생성하세요.

---
{meeting_text}
---"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                response_mime_type="application/json",
                response_schema=PANELS_SCHEMA,
            ),
        )

        if not response.text:
            raise ValueError(f"LLM 응답이 비어있습니다: {response}")

        import json
        panels_data = json.loads(response.text)

        return [PanelScenario(**panel) for panel in panels_data]


llm_service = LLMService()
