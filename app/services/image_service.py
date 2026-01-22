import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from google import genai
from google.genai import types

from app.config import settings


class ImageServiceInterface(ABC):
    """이미지 생성 서비스 인터페이스"""

    @abstractmethod
    async def generate_image(self, prompt: str) -> str:
        """프롬프트로 이미지를 생성하고 저장된 경로 반환"""
        pass


class NanoBananaImageService(ImageServiceInterface):
    """NanoBanana (Gemini Image) API를 사용한 이미지 생성 서비스"""

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.5-flash-preview-04-17"  # 이미지 생성 지원 모델
        self.images_dir = Path(settings.images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)

    async def generate_image(self, prompt: str) -> str:
        """Gemini API로 이미지 생성 후 로컬에 저장"""
        # 이미지 생성 요청
        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # 이미지 추출 및 저장
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                # 고유 파일명 생성
                filename = f"{uuid.uuid4()}.png"
                filepath = self.images_dir / filename

                # 이미지 저장
                image_data = part.inline_data.data
                with open(filepath, "wb") as f:
                    f.write(image_data)

                # 웹에서 접근 가능한 경로 반환
                return f"/static/images/{filename}"

        raise ValueError("이미지 생성 실패: 응답에 이미지가 없습니다")


image_service = NanoBananaImageService()
