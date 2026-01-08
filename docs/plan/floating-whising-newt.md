# Phase 2 Node B - Custom Search JSON API 実装プラン

## 概要

Google Custom Search JSON APIを使用して画像検索機能を実装する。
- Gemini Visionで画像から商品名/特徴を推定 → Custom Searchでテキスト検索
- 検索結果を基にLLMで「既製品(mass_product)」vs「特注品(unique_item)」を判定

---

## Google Cloud 設定手順

### 1. Custom Search API 有効化
```
Google Cloud Console → APIとサービス → ライブラリ → "Custom Search API" を有効化
```

### 2. APIキー作成
```
Google Cloud Console → 認証情報 → 認証情報を作成 → APIキー
（APIキーの制限を設定推奨: Custom Search APIのみ許可）
```

### 3. Programmable Search Engine 作成
1. https://programmablesearchengine.google.com/ にアクセス
2. 「新しい検索エンジン」作成
3. 設定:
   - 検索対象: 「ウェブ全体を検索」を有効化
   - 画像検索: 有効化
4. 検索エンジンID（cx）をメモ

### 4. 環境変数追加（.env）
```env
GOOGLE_CUSTOM_SEARCH_API_KEY=your_api_key
GOOGLE_CUSTOM_SEARCH_CX=your_search_engine_id
```

---

## 料金

| 項目 | 料金 |
|-----|------|
| Custom Search API | 無料: 100クエリ/日、有料: $5/1000クエリ |

**月間1万クエリの場合**: 約$35/月

---

## 実装フロー

```
画像 → [Vision Node] → processable判定
                ↓
      [Search Node]
         ├─ Step 1: Gemini Visionで画像から商品名/キーワード抽出
         ├─ Step 2: Custom Search APIでテキスト検索
         └─ Step 3: 検索結果を基にmass_product/unique_item判定
```

---

## 修正/作成するファイル

| ファイル | 変更内容 |
|---------|---------|
| [config.py](src/backend/core/config.py) | `GOOGLE_CUSTOM_SEARCH_API_KEY`, `GOOGLE_CUSTOM_SEARCH_CX` 追加 |
| [search/node.py](src/backend/features/agent/search/node.py) | `mock_image_search()` を Custom Search API実装に置換 |

---

## 実装詳細

### 1. config.py の変更

```python
# Custom Search API 設定
GOOGLE_CUSTOM_SEARCH_API_KEY: str  # .envで設定必須
GOOGLE_CUSTOM_SEARCH_CX: str       # .envで設定必須
```

### 2. search/node.py の変更

```python
import httpx

async def extract_search_query(image_messages: list) -> str:
    """
    Gemini Visionで画像から検索クエリを生成
    """
    llm = ChatGoogleGenerativeAI(...)
    prompt = "この画像の商品名、ブランド、特徴を簡潔に説明してください。検索クエリとして使用します。"
    # 画像を渡して商品情報を抽出
    result = await llm.ainvoke([...])
    return result.content

async def custom_search(query: str) -> list[SearchResult]:
    """
    Google Custom Search APIで検索
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": settings.GOOGLE_CUSTOM_SEARCH_API_KEY,
        "cx": settings.GOOGLE_CUSTOM_SEARCH_CX,
        "q": query,
        "searchType": "image",  # 画像検索
        "num": 5,  # 最大10件
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()

    results = []
    for item in data.get("items", []):
        results.append(SearchResult(
            product_name=item.get("title"),
            source_url=item.get("link"),
            similarity_score=0.8,  # Custom Searchは類似度を返さないため固定値
            is_exact_match=False,
        ))
    return results
```

### 3. search_node() の変更

```python
async def search_node(state: AgentState) -> dict:
    # Step 1: 画像から検索クエリを生成
    query = await extract_search_query(state.get("messages", []))

    # Step 2: Custom Search APIで検索
    search_results = await custom_search(query)

    # Step 3: LLMで分類判定（既存ロジック）
    ...
```

---

## 実装順序

1. Google Cloud設定（API有効化、APIキー作成、Search Engine作成）
2. `.env` に環境変数追加
3. `config.py` 更新（Custom Search設定追加）
4. `search/node.py` 更新（Custom Search API実装）
5. テスト実行

---

## 検証方法

1. `/agent/search_test` エンドポイントで画像を送信
2. 確認項目:
   - Geminiが画像から適切な検索クエリを生成しているか
   - Custom Search APIが結果を返しているか
   - mass_product/unique_item判定が正しいか

---

## 注意点

- Custom Search APIは「画像の見た目」での逆引き検索ではなく、テキストベース検索
- 画像から商品名を正確に抽出できるかがポイント
- 精度が不十分な場合はSerpAPI（Google Lens対応）への移行を検討
