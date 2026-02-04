import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from io import BytesIO

import httpx
import boto3
from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)


class ImageServiceInterface(ABC):
    """이미지 생성 서비스 인터페이스"""

    @abstractmethod
    async def generate_image(self, prompt: str) -> str:
        """프롬프트로 이미지를 생성하고 URL 반환"""
        pass

    @abstractmethod
    async def generate_image_with_reference(self, prompt: str, reference_image_url: str) -> str:
        """레퍼런스 이미지를 참조하여 이미지를 생성하고 URL 반환"""
        pass


class NanoBananaImageService(ImageServiceInterface):
    """NanoBanana (Gemini Image) API를 사용한 이미지 생성 서비스"""

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-3-pro-image-preview"
        self.flash_model = "gemini-2.5-flash-image"

        # S3 클라이언트
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        self.bucket = settings.s3_bucket

    async def _generate_with_retry(self, prompt: str, model: str = None):
        """재시도 로직이 포함된 이미지 생성 (즉시 3회 시도)"""
        model = model or self.model
        last_error = None

        for attempt in range(3):
            try:
                return await self.client.aio.models.generate_content(
                    model=model,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        image_config=types.ImageConfig(
                            aspect_ratio="9:16",
                            image_size="2K",
                        ),
                        response_modalities=["IMAGE", "TEXT"],
                    ),
                )
            except Exception as e:
                last_error = e
                logger.warning(f"이미지 생성 실패 (시도 {attempt + 1}/3): {type(e).__name__}: {e}")

        logger.error(f"이미지 생성 최종 실패: {type(last_error).__name__}: {last_error}")
        raise last_error

    def upload_to_s3(self, image_data: bytes, filename: str) -> str:
        """바이트 데이터를 S3에 업로드하고 URL 반환"""
        self.s3.upload_fileobj(
            BytesIO(image_data),
            self.bucket,
            filename,
            ExtraArgs={"ContentType": "image/png", "ACL": "public-read"},
        )
        return f"https://{self.bucket}.s3.{settings.s3_region}.amazonaws.com/{filename}"

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

    async def generate_image_fast(self, prompt: str) -> str:
        """Flash 모델로 빠른 이미지 생성 (캐릭터 시트용)"""
        last_error = None

        for attempt in range(3):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.flash_model,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        image_config=types.ImageConfig(
                            aspect_ratio="9:16",
                            # Flash 모델은 image_size 미지원
                        ),
                        response_modalities=["IMAGE", "TEXT"],
                    ),
                )
                break
            except Exception as e:
                last_error = e
                logger.warning(f"Flash 이미지 생성 실패 (시도 {attempt + 1}/3): {type(e).__name__}: {e}")
        else:
            logger.error(f"Flash 이미지 생성 최종 실패: {type(last_error).__name__}: {last_error}")
            raise last_error

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

    async def _fetch_image(self, url: str) -> bytes:
        """URL에서 이미지 다운로드"""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def _generate_with_reference_retry(self, prompt: str, reference_image: bytes):
        """레퍼런스 이미지를 참조하여 이미지 생성 (즉시 3회 시도)"""
        reference_instruction = """The attached image is a CHARACTER SHEET and STYLE REFERENCE.
You MUST maintain exactly:
- Same character designs (appearance, clothing, accessories)
- Same art style (line thickness, coloring method)
- Same color palette and tone
- Same background atmosphere

Now draw the following scene using these characters and style:

"""
        last_error = None

        for attempt in range(3):
            try:
                return await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=[
                        types.Part.from_bytes(data=reference_image, mime_type="image/png"),
                        reference_instruction + prompt,
                    ],
                    config=types.GenerateContentConfig(
                        image_config=types.ImageConfig(
                            aspect_ratio="9:16",
                            image_size="2K",
                        ),
                        response_modalities=["IMAGE", "TEXT"],
                    ),
                )
            except Exception as e:
                last_error = e
                logger.warning(f"레퍼런스 이미지 생성 실패 (시도 {attempt + 1}/3): {type(e).__name__}: {e}")

        logger.error(f"레퍼런스 이미지 생성 최종 실패: {type(last_error).__name__}: {last_error}")
        raise last_error

    async def generate_image_with_reference(self, prompt: str, reference_image_url: str) -> str:
        """레퍼런스 이미지를 참조하여 이미지 생성 후 S3에 업로드"""
        # 레퍼런스 이미지 다운로드
        reference_image = await self._fetch_image(reference_image_url)

        # 레퍼런스와 함께 이미지 생성
        response = await self._generate_with_reference_retry(prompt, reference_image)

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
