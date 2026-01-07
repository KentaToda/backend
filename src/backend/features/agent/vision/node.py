from langchain_google_genai import ChatGoogleGenerativeAI 
from langchain_core.messages import SystemMessage

from backend.features.agent.vision.schema import InitialAnalysis
from backend.core.config import settings
from backend.features.agent.state import AgentState

def vision_node(state: "AgentState"):    
    # Vertex AI モデルの初期化
    llm = ChatGoogleGenerativeAI(
        model=settings.MODEL_VISION_NODE, 
        project=settings.GCP_PROJECT_ID,
        location=settings.GCP_LOCATION,
        temperature=0,
        max_retries=2
    )
    
    # 構造化出力を強制する (Geminiもこのメソッドに対応しています)
    structured_llm = llm.with_structured_output(InitialAnalysis)

    system_prompt = """
    あなたは熟練の鑑定士AIエージェント『Ojoya』の「目」です。
    ユーザーから送られた画像を分析し、以下のルールに従って厳密に分類してください。

    【分類ルール】
    1. prohibited (禁止物):
       - 人物の顔、個人情報、現金、生物。
    2. unknown (不明):
       - 暗い、ボケている、対象が見切れている。
    3. unique_item (一点物/特注品/工芸品):
       - 型番がないハンドメイド品、美術品、サイン入りグッズ。
    4. mass_product (既製品/流通品):
       - スニーカー、カード、ブランド品、家電など型番があるもの。
    """

    # メッセージ構築
    # Vertex AIへの画像入力は langchain が標準化してくれます
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    # 推論実行
    try:
        result = structured_llm.invoke(messages)
        return {"analysis_result": result}
    except Exception as e:
        # GCPのエラーハンドリング (クオータ制限や画像フォーマットエラーなど)
        print(f"Vertex AI Error: {e}")
        # エラー時はunknownとして処理するなどの安全策を入れると良い
        return {
            "analysis_result": InitialAnalysis(
                category_type="unknown",
                confidence="low",
                reasoning=f"System Error: {str(e)}",
                retry_advice="システムエラーが発生しました。もう一度お試しください。"
            )
        }