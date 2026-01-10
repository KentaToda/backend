from langchain_google_vertexai import ChatVertexAI

from backend.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


def test_vertex():
    logger.info("Testing Vertex AI Connection...")

    try:
        # モデルの初期化
        # 環境変数 GOOGLE_APPLICATION_CREDENTIALS が設定されていることを前提とします
        llm = ChatVertexAI(model="gemini-1.5-flash")

        # テストプロンプトの送信
        response = llm.invoke("Hello, Vertex AI!")

        logger.info("--- Response from Vertex AI ---")
        logger.info(response.content)
        logger.info("-------------------------------")
        logger.info("Success! Connection established.")

    except Exception as e:
        logger.error("Connection Failed!", exc_info=True)


if __name__ == "__main__":
    setup_logging()
    test_vertex()
