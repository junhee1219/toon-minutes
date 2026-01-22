import asyncio
import uuid
from abc import ABC, abstractmethod
from io import BytesIO

import boto3
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings


class ImageServiceInterface(ABC):
    """이미지 생성 서비스 인터페이스"""

    @abstractmethod
    async def generate_image(self, prompt: str) -> str:
        """프롬프트로 이미지를 생성하고 URL 반환"""
        pass


class NanoBananaImageService(ImageServiceInterface):
    """NanoBanana (Gemini Image) API를 사용한 이미지 생성 서비스"""

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-3-pro-image-preview"

        # S3 클라이언트
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        self.bucket = settings.s3_bucket

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        reraise=True,
    )
    async def _generate_with_retry(self, prompt: str):
        """재시도 로직이 포함된 이미지 생성"""
        return await self.client.aio.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

    async def generate_image(self, prompt: str) -> str:
        """Gemini API로 이미지 생성 후 S3에 업로드"""
        response = await self._generate_with_retry(prompt)

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                filename = f"toon-minutes/{uuid.uuid4()}.png"
                image_data = part.inline_data.data

                # S3 업로드 (public-read로 설정)
                self.s3.upload_fileobj(
                    BytesIO(image_data),
                    self.bucket,
                    filename,
                    ExtraArgs={
                        "ContentType": "image/png",
                        "ACL": "public-read",
                    },
                )

                # S3 URL 반환
                return f"https://{self.bucket}.s3.{settings.s3_region}.amazonaws.com/{filename}"

        raise ValueError("이미지 생성 실패: 응답에 이미지가 없습니다")


image_service = NanoBananaImageService()
