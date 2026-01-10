# Firestore データ構造

## 概要

Ojoyaでは Firestore を使用してユーザー情報と査定履歴を管理します。
**フロントエンドから Firestore に直接アクセスすることはできません。すべてのデータアクセスはバックエンドAPI経由で行います。**

## コレクション構造

```
firestore-root/
├── users/{userId}/                 # ユーザードキュメント
│   ├── (profile fields)            # プロフィール情報
│   └── appraisals/{appraisalId}/   # 査定履歴（サブコレクション）
│
└── user_tickets/{userId}/          # チケット管理（将来実装予定）
```

## ドキュメント定義

### users/{userId}

ユーザープロフィール情報。`userId` は Firebase Auth の `uid` です。

```typescript
interface UserDocument {
  uid: string;                      // Firebase Auth uid
  created_at: Timestamp;            // アカウント作成日時
  last_active_at: Timestamp;        // 最終アクティブ日時
  platform: "web" | "ios" | "android";  // 登録時のプラットフォーム
  total_appraisals: number;         // 総査定回数
  account_status: "active" | "suspended";  // アカウント状態
}
```

### users/{userId}/appraisals/{appraisalId}

査定履歴ドキュメント。

```typescript
interface AppraisalDocument {
  // メタデータ
  id: string;                       // ドキュメントID
  created_at: Timestamp;            // 査定実行日時
  updated_at: Timestamp;            // 最終更新日時

  // 入力情報
  image_url?: string;               // Cloud Storage上の画像URL（オプション）
  user_comment?: string;            // ユーザーからの補足コメント

  // Vision Node結果
  vision: {
    category_type: "processable" | "unknown" | "prohibited";
    item_name: string | null;
    visual_features: string[];
    confidence: "high" | "medium" | "low";
    reasoning: string;
    retry_advice?: string;
  };

  // Search Node結果（processableの場合のみ）
  search?: {
    classification: "mass_product" | "unique_item";
    confidence: "high" | "medium" | "low";
    reasoning: string;
    identified_product: string | null;
  };

  // Price Node結果（mass_productの場合のみ）
  price?: {
    status: "complete" | "error";
    min_price: number;
    max_price: number;
    currency: "JPY";
    confidence: "high" | "medium" | "low";
    display_message: string;
    price_factors?: string[];
  };

  // 一点物の追加情報（将来の再査定フロー用）
  unique_item_details?: {
    requires_expert: boolean;
    expert_request_status: "none" | "requested" | "completed";
    additional_info?: string;
  };

  // 全体ステータス
  overall_status: "completed" | "incomplete" | "error" | "pending_reappraisal";

  // 終了ポイント（デバッグ・分析用）
  termination_point:
    | "vision_prohibited"
    | "vision_unknown"
    | "search_unique"
    | "price_complete"
    | "price_error";
}
```

## overall_status の説明

| 値 | 説明 |
|----|------|
| `completed` | 査定が正常に完了（価格算出 or 一点物判定） |
| `incomplete` | 査定が途中で終了（unknown/prohibited） |
| `error` | 価格検索でエラーが発生 |
| `pending_reappraisal` | 再査定待ち（将来機能） |

## termination_point の説明

| 値 | 説明 |
|----|------|
| `vision_prohibited` | 禁止物として判定され終了 |
| `vision_unknown` | 不明として判定され終了 |
| `search_unique` | 一点物として判定され終了 |
| `price_complete` | 価格検索が成功して終了 |
| `price_error` | 価格検索でエラーが発生して終了 |

## データアクセス方法

**重要: フロントエンドから Firestore に直接アクセスすることはできません。**

すべてのデータアクセスはバックエンドAPI経由で行います。

### 査定履歴の取得（API経由）

```typescript
// lib/api.ts
import { auth } from '@/lib/firebase';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

// 査定履歴の取得
export async function getAppraisalHistory(limit = 20, offset = 0) {
  const token = await auth.currentUser?.getIdToken();
  if (!token) throw new Error('Not authenticated');

  const response = await fetch(
    `${API_BASE_URL}/api/v1/appraisals?limit=${limit}&offset=${offset}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error('Failed to fetch appraisal history');
  }

  return response.json();
}

// 特定の査定結果を取得
export async function getAppraisal(appraisalId: string) {
  const token = await auth.currentUser?.getIdToken();
  if (!token) throw new Error('Not authenticated');

  const response = await fetch(
    `${API_BASE_URL}/api/v1/appraisals/${appraisalId}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    if (response.status === 404) return null;
    throw new Error('Failed to fetch appraisal');
  }

  return response.json();
}

// ユーザー情報の取得
export async function getUserProfile() {
  const token = await auth.currentUser?.getIdToken();
  if (!token) throw new Error('Not authenticated');

  const response = await fetch(`${API_BASE_URL}/api/v1/users/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch user profile');
  }

  return response.json();
}
```

### React Hook での使用例

```typescript
// hooks/useAppraisalHistory.ts
import { useState, useEffect } from 'react';
import { useAuth } from './useAuth';
import { getAppraisalHistory } from '@/lib/api';

export function useAppraisalHistory(limit = 20) {
  const { user } = useAuth();
  const [appraisals, setAppraisals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!user) {
      setAppraisals([]);
      setLoading(false);
      return;
    }

    const fetchHistory = async () => {
      try {
        setLoading(true);
        const data = await getAppraisalHistory(limit);
        setAppraisals(data);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Unknown error'));
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [user, limit]);

  const refresh = async () => {
    if (!user) return;
    setLoading(true);
    try {
      const data = await getAppraisalHistory(limit);
      setAppraisals(data);
    } finally {
      setLoading(false);
    }
  };

  return { appraisals, loading, error, refresh };
}
```

### コンポーネントでの使用例

```tsx
// components/AppraisalHistory.tsx
import { useAppraisalHistory } from '@/hooks/useAppraisalHistory';

export function AppraisalHistory() {
  const { appraisals, loading, error, refresh } = useAppraisalHistory();

  if (loading) return <div>読み込み中...</div>;
  if (error) return <div>エラー: {error.message}</div>;
  if (appraisals.length === 0) return <div>履歴がありません</div>;

  return (
    <div>
      <button onClick={refresh}>更新</button>
      <ul>
        {appraisals.map((appraisal) => (
          <li key={appraisal.id}>
            {appraisal.vision?.item_name || '不明な商品'}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

## セキュリティルール

フロントエンドからの Firestore への直接アクセスはすべて拒否されます。

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // すべてのドキュメントへのアクセスを拒否
    // バックエンド（Admin SDK）経由でのみアクセス可能
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

## 注意事項

1. **アクセス制限**
   - フロントエンドから Firestore に直接アクセスすることはできません
   - すべてのデータアクセスはバックエンドAPI経由で行います
   - バックエンドは Firebase Admin SDK を使用してアクセスします

2. **認証**
   - APIリクエストには Firebase ID Token が必要です
   - `Authorization: Bearer <token>` ヘッダーを設定してください

3. **リアルタイム更新**
   - Firestore のリアルタイムリスナーは使用できません
   - 最新データが必要な場合はAPIを再度呼び出してください
   - ポーリングまたは手動更新ボタンで対応してください

4. **Timestamp の扱い**
   - APIレスポンスの日時フィールドは ISO 8601 形式の文字列で返されます
   - JavaScript の `Date` に変換する場合は `new Date(timestamp)` を使用してください

```typescript
const createdAt = new Date(appraisal.created_at);
console.log(createdAt.toLocaleDateString('ja-JP'));
```
