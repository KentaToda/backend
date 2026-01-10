# 査定API仕様書

## 概要

画像から商品を特定し、中古相場を提示するAPIエンドポイントです。

## エンドポイント

```
POST /api/v1/analyze
```

## 認証

- **オプション**: `Authorization` ヘッダーに Firebase ID Token を設定
- 認証済みの場合: 査定結果が Firestore に保存され、履歴として閲覧可能
- 未認証の場合: 査定のみ実行（保存なし）

```
Authorization: Bearer <Firebase ID Token>
```

## リクエスト

### Headers

| ヘッダー | 必須 | 説明 |
|---------|------|------|
| Content-Type | Yes | `application/json` |
| Authorization | No | `Bearer <Firebase ID Token>` |

### Body

```typescript
interface AnalyzeRequest {
  // Base64エンコードされた画像（data URI形式）
  image_base64: string;  // 例: "data:image/jpeg;base64,/9j/4AAQ..."

  // ユーザーからの補足コメント（任意）
  user_comment?: string;

  // クライアントプラットフォーム
  platform?: "web" | "ios" | "android";  // デフォルト: "web"
}
```

### リクエスト例

```json
{
  "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...",
  "user_comment": "3年前に購入しました",
  "platform": "web"
}
```

## レスポンス

### 成功時 (200 OK)

```typescript
interface AnalyzeResponse {
  // 査定ID（認証済みユーザーのみ）
  appraisal_id: string | null;

  // 商品情報
  item_name: string | null;           // 推定商品名
  identified_product: string | null;  // 特定された商品名（属性込み）
  visual_features: string[];          // 視覚的特徴

  // 分類
  classification: "mass_product" | "unique_item" | "unknown" | "prohibited";

  // 価格情報（既製品の場合のみ）
  price: PriceInfo | null;

  // 信頼度
  confidence: ConfidenceInfo | null;

  // 価格変動要因（既製品の場合のみ）
  price_factors: string[] | null;

  // メッセージ（一点物や査定不可の場合）
  message: string | null;
  recommendation: string | null;
  retry_advice: string | null;
}

interface PriceInfo {
  min_price: number;      // 最低価格（円）
  max_price: number;      // 最高価格（円）
  currency: string;       // 通貨（"JPY"）
  display_message: string; // 表示用メッセージ
}

interface ConfidenceInfo {
  level: "high" | "medium" | "low";
  reasoning: string;      // 判定理由
}
```

## レスポンス例

### 既製品（mass_product）の場合

```json
{
  "appraisal_id": "20260111123456_abc12345",
  "item_name": "NIKE Air Max 90",
  "identified_product": "NIKE Air Max 90, 白",
  "visual_features": ["白", "スニーカー", "美品", "現行モデル"],
  "classification": "mass_product",
  "price": {
    "min_price": 8000,
    "max_price": 15000,
    "currency": "JPY",
    "display_message": "メルカリでの一般的な中古相場です"
  },
  "confidence": {
    "level": "high",
    "reasoning": "同一商品の取引実績が多数確認できました"
  },
  "price_factors": [
    "2020年以降のモデルは10000-15000円、それ以前は6000-10000円",
    "箱・付属品ありで+1000-2000円",
    "未使用品は15000-20000円"
  ],
  "message": null,
  "recommendation": null,
  "retry_advice": null
}
```

### 一点物（unique_item）の場合

```json
{
  "appraisal_id": "20260111123456_def67890",
  "item_name": "手作り陶芸 花瓶",
  "identified_product": null,
  "visual_features": ["青い釉薬", "大型", "手作り感"],
  "classification": "unique_item",
  "price": null,
  "confidence": {
    "level": "high",
    "reasoning": "市場に同一商品の流通が確認できませんでした"
  },
  "price_factors": null,
  "message": "一点物のため市場価格の算出が困難です",
  "recommendation": "専門家による査定をお勧めします",
  "retry_advice": null
}
```

### 査定不可（unknown）の場合

```json
{
  "appraisal_id": null,
  "item_name": null,
  "identified_product": null,
  "visual_features": [],
  "classification": "unknown",
  "price": null,
  "confidence": {
    "level": "low",
    "reasoning": "画像が暗すぎて商品を判別できませんでした"
  },
  "price_factors": null,
  "message": "画像から商品を特定できませんでした",
  "recommendation": null,
  "retry_advice": "明るい場所で商品全体が写るように撮影してください"
}
```

### 禁止物（prohibited）の場合

```json
{
  "appraisal_id": null,
  "item_name": null,
  "identified_product": null,
  "visual_features": [],
  "classification": "prohibited",
  "price": null,
  "confidence": {
    "level": "high",
    "reasoning": "人物の顔が含まれています"
  },
  "price_factors": null,
  "message": "この画像は査定対象外です",
  "recommendation": null,
  "retry_advice": "商品のみが写った画像を使用してください"
}
```

## エラーレスポンス

### 認証エラー (401 Unauthorized)

```json
{
  "detail": "トークンの有効期限が切れています"
}
```

| エラーコード | メッセージ |
|-------------|-----------|
| token_expired | トークンの有効期限が切れています |
| token_revoked | トークンが取り消されています |
| invalid_token | 無効なトークンです |
| invalid_auth_format | 無効な認証形式です |

### サーバーエラー (500 Internal Server Error)

```json
{
  "detail": "Internal Server Error"
}
```

## 分類（classification）の説明

| 値 | 説明 | 価格情報 |
|----|------|---------|
| `mass_product` | 既製品（ブランド品、量産品など） | あり |
| `unique_item` | 一点物（手作り品、アート作品など） | なし |
| `unknown` | 画像から商品を特定できない | なし |
| `prohibited` | 査定対象外（人物、現金など） | なし |

## 信頼度（confidence.level）の説明

| 値 | 説明 |
|----|------|
| `high` | 同一商品の取引実績が多数確認できた |
| `medium` | 類似商品は見つかるが、完全一致は見つからない |
| `low` | 関連情報が少なく、確信度が低い |

## 実装例

### JavaScript (fetch)

```javascript
async function analyzeImage(imageBase64, idToken = null) {
  const headers = {
    'Content-Type': 'application/json',
  };

  if (idToken) {
    headers['Authorization'] = `Bearer ${idToken}`;
  }

  const response = await fetch('/api/v1/analyze', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      image_base64: imageBase64,
      platform: 'web',
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  return response.json();
}
```

### TypeScript (axios)

```typescript
import axios from 'axios';

interface AnalyzeRequest {
  image_base64: string;
  user_comment?: string;
  platform?: 'web' | 'ios' | 'android';
}

interface AnalyzeResponse {
  appraisal_id: string | null;
  item_name: string | null;
  identified_product: string | null;
  visual_features: string[];
  classification: 'mass_product' | 'unique_item' | 'unknown' | 'prohibited';
  price: {
    min_price: number;
    max_price: number;
    currency: string;
    display_message: string;
  } | null;
  confidence: {
    level: 'high' | 'medium' | 'low';
    reasoning: string;
  } | null;
  price_factors: string[] | null;
  message: string | null;
  recommendation: string | null;
  retry_advice: string | null;
}

async function analyzeImage(
  request: AnalyzeRequest,
  idToken?: string
): Promise<AnalyzeResponse> {
  const headers: Record<string, string> = {};

  if (idToken) {
    headers['Authorization'] = `Bearer ${idToken}`;
  }

  const { data } = await axios.post<AnalyzeResponse>(
    '/api/v1/analyze',
    request,
    { headers }
  );

  return data;
}
```

### 画像のBase64変換

```javascript
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = (error) => reject(error);
  });
}

// 使用例
const fileInput = document.getElementById('image-input');
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  const base64 = await fileToBase64(file);
  const result = await analyzeImage(base64);
  console.log(result);
});
```
