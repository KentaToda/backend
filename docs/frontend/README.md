# フロントエンド実装ガイド

Ojoya フロントエンド実装のためのドキュメント集です。

## ドキュメント一覧

| ドキュメント | 説明 |
|-------------|------|
| [firebase_auth.md](./firebase_auth.md) | Firebase Anonymous Auth の実装方法 |
| [firestore_schema.md](./firestore_schema.md) | Firestore のデータ構造と読み取り方法 |
| [ui_guidelines.md](./ui_guidelines.md) | UIコンポーネントの実装ガイドライン |
| [../api/analyze_endpoint.md](../api/analyze_endpoint.md) | 査定APIの仕様書 |

## クイックスタート

### 1. Firebase の設定

```bash
npm install firebase
```

```typescript
// lib/firebase.ts
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
```

### 2. 認証フックの作成

```typescript
// hooks/useAuth.ts
import { useState, useEffect } from 'react';
import { signInAnonymously, onAuthStateChanged, User } from 'firebase/auth';
import { auth } from '@/lib/firebase';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    return onAuthStateChanged(auth, (user) => {
      setUser(user);
      setLoading(false);
    });
  }, []);

  const signIn = () => signInAnonymously(auth);
  const getToken = () => user?.getIdToken();

  return { user, loading, signIn, getToken };
}
```

### 3. 査定APIの呼び出し

```typescript
// lib/api.ts
import { auth } from '@/lib/firebase';

export async function analyzeImage(imageBase64: string) {
  const token = await auth.currentUser?.getIdToken();

  const response = await fetch('/api/v1/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify({
      image_base64: imageBase64,
      platform: 'web',
    }),
  });

  if (!response.ok) {
    throw new Error('査定に失敗しました');
  }

  return response.json();
}
```

### 4. 基本的なコンポーネント

```tsx
// components/Appraisal.tsx
import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { analyzeImage } from '@/lib/api';

export function Appraisal() {
  const { user, signIn } = useAuth();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (imageBase64: string) => {
    if (!user) await signIn();

    setLoading(true);
    try {
      const data = await analyzeImage(imageBase64);
      setResult(data);
    } finally {
      setLoading(false);
    }
  };

  // ... UI実装
}
```

## レスポンス形式の概要

### 分類（classification）

| 値 | 説明 | 価格情報 |
|----|------|---------|
| `mass_product` | 既製品 | あり |
| `unique_item` | 一点物 | なし |
| `unknown` | 特定不可 | なし |
| `prohibited` | 査定対象外 | なし |

### 主要フィールド

- `appraisal_id`: 査定ID（認証済みの場合のみ）
- `item_name`: 推定商品名
- `identified_product`: 特定された商品名
- `price`: 価格情報（min_price, max_price, display_message）
- `price_factors`: 価格変動要因のリスト
- `confidence`: 信頼度（level, reasoning）
- `message`: エラーや補足メッセージ
- `retry_advice`: 再撮影のアドバイス

## 環境変数

```env
# .env.local
NEXT_PUBLIC_FIREBASE_API_KEY=xxx
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=xxx.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=xxx
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## サポート

質問や問題がある場合は、バックエンドチームに連絡してください。
