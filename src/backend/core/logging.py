"""
ロギング設定モジュール
- Cloud Logging互換のJSON形式をサポート
- 環境変数でログレベル制御
"""
import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any


class CloudLoggingFormatter(logging.Formatter):
    """
    Cloud Logging互換のJSON形式フォーマッター
    ローカル開発時は人間可読形式、本番はJSON形式
    """

    def __init__(self, json_format: bool = False):
        super().__init__()
        self.json_format = json_format

    def format(self, record: logging.LogRecord) -> str:
        if self.json_format:
            # Cloud Logging互換のJSON形式
            log_entry: dict[str, Any] = {
                "severity": record.levelname,
                "message": record.getMessage(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "logging.googleapis.com/sourceLocation": {
                    "file": record.filename,
                    "line": record.lineno,
                    "function": record.funcName,
                },
                "logger": record.name,
            }
            if record.exc_info:
                log_entry["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_entry, ensure_ascii=False)
        else:
            # ローカル開発用の人間可読形式
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return f"{timestamp} [{record.levelname}] {record.name}: {record.getMessage()}"


def setup_logging() -> logging.Logger:
    """
    アプリケーション全体のロギング設定を初期化
    """
    # 循環インポートを避けるためここでインポート
    from backend.core.config import settings

    # ログレベルの決定（環境変数から取得、デフォルトはINFO）
    log_level_str = getattr(settings, "LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # 本番環境かどうかの判定
    is_production = getattr(settings, "ENVIRONMENT", "development") == "production"

    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 既存のハンドラーをクリア
    root_logger.handlers.clear()

    # ストリームハンドラーを追加
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(CloudLoggingFormatter(json_format=is_production))
    root_logger.addHandler(handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    モジュール用のロガーを取得

    使用例:
        from backend.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Processing started")
    """
    return logging.getLogger(name)
