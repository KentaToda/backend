"""
LLM呼び出しの自動ログ出力モジュール

LangChainのCallbacks機能を使用して、LLM呼び出しを自動的にログ出力する。
"""
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from backend.core.logging import get_logger


class LLMLoggingHandler(BaseCallbackHandler):
    """LLM呼び出しの自動ログ出力ハンドラー"""

    def __init__(self, node_name: str = "llm"):
        self.logger = get_logger(f"llm.{node_name}")
        self.node_name = node_name

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        """LLM呼び出し開始時のログ"""
        model = serialized.get("kwargs", {}).get("model", "unknown")
        self.logger.info(f"LLM START: model={model}")
        # プロンプトはDEBUGレベルで出力（長いため）
        for i, prompt in enumerate(prompts):
            truncated = prompt[:200] + "..." if len(prompt) > 200 else prompt
            self.logger.debug(f"Prompt[{i}]: {truncated}")

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """LLM呼び出し終了時のログ"""
        # トークン使用量をログ
        llm_output = response.llm_output or {}
        usage = llm_output.get("token_usage", {})
        if usage:
            self.logger.info(
                f"LLM END: input={usage.get('prompt_tokens')}, "
                f"output={usage.get('completion_tokens')}"
            )
        else:
            self.logger.info("LLM END")

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """LLMエラー時のログ"""
        self.logger.error(f"LLM ERROR: {error}", exc_info=True)


def get_llm_callbacks(node_name: str) -> list[BaseCallbackHandler]:
    """
    ノード用のCallbackリストを取得

    使用例:
        from backend.core.llm_callbacks import get_llm_callbacks

        # LLM初期化時にデフォルトCallbackを設定
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            callbacks=get_llm_callbacks("vision"),
        )

        # または、invoke時に指定
        result = llm.invoke(messages, config={"callbacks": get_llm_callbacks("vision")})
    """
    return [LLMLoggingHandler(node_name)]
