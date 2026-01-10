"""
Firebase Admin SDK 初期化モジュール

- Cloud Run環境ではADC（Application Default Credentials）を自動使用
- ローカル開発時はGOOGLE_APPLICATION_CREDENTIALS環境変数を使用
"""
import os
from functools import lru_cache
from typing import Optional

import firebase_admin
from firebase_admin import auth, credentials

from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


class AuthError(Exception):
    """認証エラー"""

    def __init__(self, message: str, code: str = "auth_error"):
        self.message = message
        self.code = code
        super().__init__(self.message)


def _get_credentials() -> credentials.Base:
    """
    認証情報を取得

    - GOOGLE_APPLICATION_CREDENTIALS 環境変数があればそれを使用
    - なければ ADC (Application Default Credentials) を使用
    """
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if creds_path and os.path.exists(creds_path):
        logger.info(f"Using credentials from: {creds_path}")
        return credentials.Certificate(creds_path)
    else:
        logger.info("Using Application Default Credentials (ADC)")
        return credentials.ApplicationDefault()


@lru_cache(maxsize=1)
def initialize_firebase() -> firebase_admin.App:
    """
    Firebase Admin SDKを初期化（シングルトン）

    複数回呼び出されても一度だけ初期化される。
    """
    if firebase_admin._apps:
        logger.debug("Firebase already initialized")
        return firebase_admin.get_app()

    try:
        cred = _get_credentials()
        app = firebase_admin.initialize_app(
            cred,
            {
                "projectId": settings.GCP_PROJECT_ID,
            },
        )
        logger.info(f"Firebase initialized for project: {settings.GCP_PROJECT_ID}")
        return app
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}", exc_info=True)
        raise


def verify_id_token(id_token: str, check_revoked: bool = False) -> dict:
    """
    Firebase ID Token を検証し、デコードされたトークン情報を返す

    Args:
        id_token: クライアントから送信された ID Token
        check_revoked: トークンが取り消されているかチェックするか（デフォルト: False）

    Returns:
        デコードされたトークン情報（uid, email, etc.）

    Raises:
        AuthError: トークンが無効な場合
    """
    initialize_firebase()

    try:
        decoded_token = auth.verify_id_token(id_token, check_revoked=check_revoked)
        logger.debug(f"Token verified for uid: {decoded_token.get('uid')}")
        return decoded_token
    except auth.ExpiredIdTokenError:
        logger.warning("Expired ID token")
        raise AuthError("トークンの有効期限が切れています", code="token_expired")
    except auth.RevokedIdTokenError:
        logger.warning("Revoked ID token")
        raise AuthError("トークンが取り消されています", code="token_revoked")
    except auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid ID token: {e}")
        raise AuthError("無効なトークンです", code="invalid_token")
    except Exception as e:
        logger.error(f"Token verification error: {e}", exc_info=True)
        raise AuthError(f"認証エラー: {str(e)}", code="auth_error")


def get_user_from_token(id_token: str) -> Optional[dict]:
    """
    ID Token からユーザー情報を取得

    Args:
        id_token: クライアントから送信された ID Token

    Returns:
        ユーザー情報を含む辞書、または None（検証失敗時）
    """
    try:
        decoded_token = verify_id_token(id_token)
        return {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "email_verified": decoded_token.get("email_verified", False),
            "provider_id": decoded_token.get("firebase", {}).get("sign_in_provider"),
            "is_anonymous": decoded_token.get("firebase", {}).get("sign_in_provider") == "anonymous",
        }
    except AuthError:
        return None


async def get_current_user_id(authorization: Optional[str]) -> str:
    """
    Authorization ヘッダーからユーザーIDを取得

    Args:
        authorization: "Bearer <token>" 形式の Authorization ヘッダー

    Returns:
        ユーザーID (Firebase uid)

    Raises:
        AuthError: 認証に失敗した場合
    """
    if not authorization:
        raise AuthError("認証が必要です", code="missing_auth")

    if not authorization.startswith("Bearer "):
        raise AuthError("無効な認証形式です", code="invalid_auth_format")

    token = authorization[7:]  # "Bearer " を除去

    if not token:
        raise AuthError("トークンが空です", code="empty_token")

    decoded_token = verify_id_token(token)
    return decoded_token["uid"]
