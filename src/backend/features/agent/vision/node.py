from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.core.config import settings
from backend.core.llm_callbacks import get_llm_callbacks
from backend.core.logging import get_logger
from backend.features.agent.state import AgentState
from backend.features.agent.vision.schema import InitialAnalysis

logger = get_logger(__name__)


def vision_node(state: "AgentState"):
    # Vertex AI モデルの初期化
    llm = ChatGoogleGenerativeAI(
        model=settings.MODEL_VISION_NODE,
        project=settings.GCP_PROJECT_ID,
        location=settings.GCP_LOCATION,
        temperature=0,
        max_retries=2,
        vertexai=True,
        callbacks=get_llm_callbacks("vision"),
    )
    
    # 構造化出力を強制する (Geminiもこのメソッドに対応しています)
    structured_llm = llm.with_structured_output(InitialAnalysis)

    system_prompt = """
あなたは熟練の鑑定士AIエージェント『Ojoya』の「目」です。
ユーザーから送られた画像を分析し、以下のルールに従って厳密に分類してください。

【このエージェントの目的】
ユーザーがフリマアプリへの出品、買取店への持ち込み、または中古品購入の価格検討に活用できる
「中古相場情報」を提供することです。そのため、後続の検索ノードで商品を特定しやすい情報を抽出してください。

【分類ルール】
1. prohibited (禁止物):
   - 人物の顔が明確に写っている画像
   - 個人情報（住所、電話番号、クレジットカードなど）が写っている
   - 現金、有価証券
   - 生きている動植物
   ※商品の一部として人物が写っている場合（モデル着用写真など）は prohibited ではない

2. unknown (不明):
   - 暗すぎて商品が判別できない
   - ピントが合っておらずぼやけている
   - 対象物が見切れていて全体像が分からない
   - 何の商品か全く判別できない

3. processable (査定可能):
   - 上記に該当しない、査定対象として有効な商品画像
   - 既製品か一点物かは次のノードで判断するため、この段階では区別しない

【processableの場合の追加タスク】
査定可能と判断した場合は、以下も抽出してください:

■ item_name（商品名）
- 後続の検索で商品を特定するための重要な情報です
- ブランド名 + 商品名/シリーズ名 の形式で出力
- 型番が視認できる場合は必ず含める
- 括弧書きや補足説明は含めない
- 例: "Louis Vuitton ネヴァーフル MM", "SEIKO プレザージュ SARX035", "NIKE Air Max 90"

■ visual_features（視覚的特徴）
後続の検索や価格算出に影響する特徴をリストで抽出:
- ブランドロゴ、刻印、タグ（認識できた場合）
- メインカラー（シンプルに: "赤", "黒", "ネイビー" など）
- 素材（レザー、キャンバス、ナイロン など）
- サイズ感（S/M/L または 大/中/小）
- 状態（新品同様, 美品, やや使用感あり, 使用感あり, ジャンク）
- 年代を示す特徴があれば（例: "旧ロゴ", "現行モデル"）
- 付属品が写っていれば（箱、保証書、袋など）

【confidenceの判断基準】
- high: ブランド・商品名が明確に特定でき、状態も判断できる
- medium: 商品カテゴリは分かるが、具体的な型番やモデルが不明確
- low: 大まかな分類のみ可能で、詳細な特定が困難

【注意事項】
- フリマアプリで使われるような、検索しやすいシンプルな単語を使用してください
- 推測で型番を付与しないでください。視認できる情報のみを記載してください
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
        logger.error(f"Vertex AI Error: {e}", exc_info=True)
        # エラー時はunknownとして処理するなどの安全策を入れると良い
        return {
            "analysis_result": InitialAnalysis(
                category_type="unknown",
                confidence="low",
                reasoning=f"System Error: {str(e)}",
                retry_advice="システムエラーが発生しました。もう一度お試しください。"
            )
        }