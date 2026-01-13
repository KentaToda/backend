"""
Cloud Storageクライアントモジュール

商品画像のアップロード・取得を担当。
"""
import base64
import io
import re
from datetime import timedelta
from typing import Optional

from google.cloud import storage
from PIL import Image

from backend.core.config import settings
from backend.core.logging import get_logger


logger = get_logger(__name__)


class StorageClient:
    """Cloud Storageクライアントのラッパー"""

    def __init__(self):
        self._client: Optional[storage.Client] = None
        self._bucket: Optional[storage.Bucket] = None

    @property
    def client(self) -> storage.Client:
        """遅延初期化でStorageクライアント取得"""
        if self._client is None:
            self._client = storage.Client()
            logger.info("Cloud Storage client initialized")
        return self._client

    @property
    def bucket(self) -> storage.Bucket:
        """バケット参照を取得"""
        if self._bucket is None:
            self._bucket = self.client.bucket(settings.GCS_BUCKET_NAME)
            logger.info(f"Using bucket: {settings.GCS_BUCKET_NAME}")
        return self._bucket

    def _decode_base64_image(self, image_base64: str) -> bytes:
        """
        Base64画像をデコード

        data:image/png;base64,... 形式とプレーンBase64の両方に対応
        """
        # Data URI形式の場合はプレフィックスを除去
        if image_base64.startswith("data:"):
            match = re.match(r"data:image/[^;]+;base64,(.+)", image_base64)
            if match:
                image_base64 = match.group(1)

        return base64.b64decode(image_base64)

    def _convert_to_webp(self, image_bytes: bytes, quality: int = 85) -> bytes:
        """
        画像をWebP形式に変換

        Args:
            image_bytes: 元画像のバイナリデータ
            quality: 画質（1-100）

        Returns:
            WebP形式のバイナリデータ
        """
        with Image.open(io.BytesIO(image_bytes)) as img:
            # RGBAの場合はRGBに変換（WebPは透過もサポートするが、写真なので不要）
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            output = io.BytesIO()
            img.save(output, format="WEBP", quality=quality)
            return output.getvalue()

    async def upload_image(
        self,
        user_id: str,
        appraisal_id: str,
        image_base64: str,
    ) -> str:
        """
        Base64画像をWebP形式でCloud Storageにアップロード

        Args:
            user_id: ユーザーID
            appraisal_id: 査定ID
            image_base64: Base64エンコードされた画像

        Returns:
            保存先のパス（gs://bucket/path 形式ではなく、相対パス）
        """
        try:
            # Base64デコード
            image_bytes = self._decode_base64_image(image_base64)

            # WebP変換
            webp_bytes = self._convert_to_webp(image_bytes)

            # アップロード先パス
            image_path = f"users/{user_id}/{appraisal_id}.webp"

            # アップロード
            blob = self.bucket.blob(image_path)
            blob.upload_from_string(webp_bytes, content_type="image/webp")

            logger.info(f"Uploaded image: {image_path} ({len(webp_bytes)} bytes)")
            return image_path

        except Exception as e:
            logger.error(f"Failed to upload image: {e}", exc_info=True)
            raise

    def get_signed_url(
        self,
        image_path: str,
        expiration_minutes: Optional[int] = None,
    ) -> str:
        """
        署名付きURLを生成

        Args:
            image_path: 画像のパス
            expiration_minutes: 有効期限（分）、Noneの場合は設定値を使用

        Returns:
            署名付きURL
        """
        if expiration_minutes is None:
            expiration_minutes = settings.GCS_IMAGE_EXPIRATION_MINUTES

        blob = self.bucket.blob(image_path)
        url = blob.generate_signed_url(
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
        )

        logger.debug(f"Generated signed URL for: {image_path}")
        return url

    async def delete_image(self, image_path: str) -> bool:
        """
        画像を削除

        Args:
            image_path: 画像のパス

        Returns:
            削除成功時はTrue
        """
        try:
            blob = self.bucket.blob(image_path)
            blob.delete()
            logger.info(f"Deleted image: {image_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete image: {e}", exc_info=True)
            return False


# シングルトンインスタンス
storage_client = StorageClient()
