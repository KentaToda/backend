"""
LLM呼び出しの自動ログ出力モジュール

LangChainのCallbacks機能を使用して、LLM呼び出しを自動的にログ出力する。
"""
import asyncio
from typing import Any, Optional

from langchain_core.callbacks import AsyncCallbackHandler, BaseCallbackHandler
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


class StreamingCallbackHandler(AsyncCallbackHandler):
    """
    LLMのトークンストリーミングをキューに送信するハンドラー

    使用例:
        queue = asyncio.Queue()
        handler = StreamingCallbackHandler(queue, "vision")

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            streaming=True,
            callbacks=[handler],
        )

        # 別タスクでキューからトークンを取得
        async for token in queue_to_async_generator(queue):
            yield token
    """

    def __init__(self, queue: asyncio.Queue, node_name: str):
        self.queue = queue
        self.node_name = node_name
        self.logger = get_logger(f"llm.stream.{node_name}")
        self._buffer = ""

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """新しいトークンが生成されたとき"""
        self._buffer += token

        # 改行を検出したら行単位で送信
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if line:
                await self.queue.put({
                    "type": "thinking",
                    "node": self.node_name,
                    "content": line,
                })

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """LLM呼び出し終了時"""
        # バッファに残っている内容を送信
        if self._buffer.strip():
            await self.queue.put({
                "type": "thinking",
                "node": self.node_name,
                "content": self._buffer.strip(),
            })
            self._buffer = ""

        # 終了シグナルを送信
        await self.queue.put({
            "type": "node_end",
            "node": self.node_name,
        })

    async def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """LLMエラー時"""
        self.logger.error(f"LLM ERROR: {error}", exc_info=True)
        await self.queue.put({
            "type": "error",
            "node": self.node_name,
            "message": str(error),
        })
