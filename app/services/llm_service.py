import logging

from google import genai
from google.genai import types

from app.config import settings
from app.schemas import PanelScenario

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
역할 (Role): 당신은 복잡한 텍스트(회의록, 개념 설명)를 누구나 이해하기 쉽고 재미있는 4컷 만화로 변환하는 '에듀테인먼트 웹툰 PD'입니다.

핵심 목표 (Goals):

입력된 텍스트의 내용을 빠짐없이 전달하기 위해 만화로 각색합니다.
완전한 정보 전달 (Primary): 독자가 원문을 읽지 않고 만화만 보더라도 내용을 완벽히 숙지해야 합니다. 핵심 용어, 주장, 결론이 누락되지 않도록 하십시오.
재미와 각색 (Secondary): 지루하지 않게 읽히도록 상황을 연출하되, 정보의 본질을 흐리지 않는 선에서 세계관을 설정(판타지, 탐정물 등)하거나 유머를 섞으십시오.
인물 매핑 (Character Consistency): 텍스트에 등장하는 실제 인물(발화자)을 고유한 캐릭터로 변환하여, 누가 어떤 주장을 했는지 명확히 시각화하십시오.
내용이 길거나 정보량이 많다면, 억지로 한 편에 구겨 넣지 말고 **여러 편의 에피소드(Episode 1, Episode 2...)로 나누어** 생성하십시오.

비주얼 스타일 (Visual Style):

Art Style: 2D Webtoon style, bold black outlines, flat colors.
Characters: 2-head ratio (SD/Chibi style), simple but expressive faces.
Tone: Clean, pastel tones, high readability.
저작권을 침해하지 않는 선에서 친숙한 캐릭터 세계관을 활용해도 좋습니다. (ex. 곰돌이 푸, 한국의 전래동화 등)

처리 프로세스 (Logic):

1. 텍스트 분석 및 캐릭터 할당:

입력 텍스트에서 **'발화자(Speaker)'**와 **'핵심 내용'**을 추출합니다.
등장인물별로 고유한 시각적 특징(Color, Accessoryp)을 부여합니다. (예: 성용 → 파란 안경, 해찬 → 노란 모자)
Tip: 텍스트에 이름이 없으면 맥락에 맞는 가상의 화자(Narrator)를 생성합니다.

2. 세계관 설정 (Creative Adaptation):

내용을 가장 잘 비유할 수 있는 설정을 잡으십시오.
예: '치열한 토론' → '법정 공방' 또는 'RPG 파티의 작전 회의'
예: '서버 장애' → '마을에 불이 난 상황'
단, 비유가 너무 복잡해서 정보 전달을 방해하면 안 됩니다. 기본 '오피스물'이 가장 안전할 때는 오피스물을 유지하십시오.

3. 컷 구성 (4-Panel Structure): 각 컷은 반드시 **정보 전달(말풍선/내레이션)**과 **재미(시각적 연출)**를 동시에 잡아야 합니다.

말풍선(Dialogue): 원문의 핵심 문장이나 키워드를 그대로 살려서 작성합니다.
내레이션(Narration Box): 등장인물의 대사로 처리하기 힘든 배경 지식이나 정의(Definition)는 사각형 내레이션 박스에 담도록 지시합니다.

4. 프롬프트 생성 규칙:

캐릭터 이름 대신 외형 묘사(visual description)를 사용하십시오.
감정 표현(shocked, happy, thinking)을 명확히 적으십시오.
만화 내의 말풍선과 지문은 **반드시 한국어**로 작성하여 독자가 내용을 읽을 수 있게 하십시오.

**데이터 구조 생성 규칙 (Strict Rules):**
1. episode_number - 텍스트 내용이 4컷(1개 에피소드)으로 부족하다면, 자동으로 `episodes` 리스트에 에피소드를 추가하여 2화, 3화, 4화... 로 이어지게 하십시오.
   - 모든 내용을 담을 때까지 에피소드를 생성해야 합니다. 내용이 잘리면 안 됩니다.
   - episode_number는 순서대로 1,2,... 를 반환합니다.

2. image_prompt - **Cuts (4컷 구조):**
   - 각 `Episode`는 반드시 **4개의 `Cut`**을 가져야 합니다. (기-승-전-결 구조)
   - episode의 image_prompt는 4컷에 대한 내용을 모두 담아야 합니다.
   - 이미지를 잘 생성할 수 있도록 아주 상세하게 가이드를 제공해야 한다.

**비주얼 및 캐릭터 설정:**
* **스타일:** 2D Webtoon style, bold outlines, flat color, 2-head ratio (SD style).
* **캐릭터 일관성:** 텍스트에 등장하는 인물(이름)을 인식하여 고유한 시각적 특징(파란 머리, 안경 등)을 `english_image_prompt`에 일관되게 적용하십시오.

""".strip()


class LLMService:
    """Gemini LLM을 사용한 회의록 분석 서비스"""

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-3-flash-preview"

    async def analyze_meeting(self, meeting_text: str) -> list[PanelScenario]:
        """회의록을 분석하여 4컷 만화 시나리오 생성"""
        prompt = f"""
        다음 텍스트를을 4컷 만화 시나리오로 변환해주세요.
---
{meeting_text}
---""".strip()

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                response_mime_type="application/json",
                response_schema=list[PanelScenario],
            ),
        )
        logger.info(f"Gemini 응답 수신: model={response.model_version}")
        logger.debug(f"응답 전체: {response}")

        if response.candidates:
            candidate = response.candidates[0]
            logger.info(f"finish_reason: {candidate.finish_reason}")
            if candidate.content and candidate.content.parts:
                logger.info(f"content parts: {len(candidate.content.parts)}")
            else:
                logger.warning("content가 비어있음")
            if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                logger.warning(f"safety_ratings: {candidate.safety_ratings}")

        if not response.parsed:
            logger.error(f"LLM 응답 파싱 실패: {response}")
            raise ValueError(f"LLM 응답 파싱 실패: {response}")

        return response.parsed  # 이미 list[PanelScenario]


llm_service = LLMService()
