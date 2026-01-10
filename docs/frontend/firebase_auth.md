# Firebase Anonymous Auth 実装ガイド

## 概要

Ojoyaでは Firebase Anonymous Auth を使用して、ユーザー登録なしで査定履歴を保存できます。
匿名ユーザーはデバイス単位で識別され、後からメールアドレス等でアカウントをアップグレードすることも可能です。

## セットアップ

### 1. Firebase プロジェクトの設定

Firebase Console で Anonymous Auth を有効化:
1. Firebase Console > Authentication > Sign-in method
2. 「匿名」を有効にする

### 2. Firebase SDK のインストール

```bash
# npm
npm install firebase

# yarn
yarn add firebase
```

### 3. Firebase の初期化

```typescript
// lib/firebase.ts
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  // ... その他の設定
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
```

## 匿名認証の実装

### 基本的な匿名サインイン

```typescript
// hooks/useAuth.ts
import { useState, useEffect } from 'react';
import {
  signInAnonymously,
  onAuthStateChanged,
  User,
} from 'firebase/auth';
import { auth } from '@/lib/firebase';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 認証状態の監視
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setUser(user);
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  // 匿名サインイン
  const signInAsAnonymous = async () => {
    try {
      const result = await signInAnonymously(auth);
      return result.user;
    } catch (error) {
      console.error('Anonymous sign-in failed:', error);
      throw error;
    }
  };

  // ID Token の取得
  const getIdToken = async (): Promise<string | null> => {
    if (!user) return null;
    try {
      return await user.getIdToken();
    } catch (error) {
      console.error('Failed to get ID token:', error);
      return null;
    }
  };

  return {
    user,
    loading,
    isAuthenticated: !!user,
    isAnonymous: user?.isAnonymous ?? false,
    signInAsAnonymous,
    getIdToken,
  };
}
```

### 自動匿名サインイン

```typescript
// hooks/useAutoAuth.ts
import { useEffect } from 'react';
import { useAuth } from './useAuth';

export function useAutoAuth() {
  const { user, loading, signInAsAnonymous } = useAuth();

  useEffect(() => {
    // ロード完了後、未認証なら自動で匿名サインイン
    if (!loading && !user) {
      signInAsAnonymous();
    }
  }, [loading, user, signInAsAnonymous]);

  return { user, loading };
}
```

## API 呼び出しとの統合

### 認証付き API クライアント

```typescript
// lib/api.ts
import { auth } from '@/lib/firebase';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

interface RequestOptions {
  method?: string;
  body?: any;
  requireAuth?: boolean;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = 'GET', body, requireAuth = true } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // 認証トークンを追加
  if (requireAuth && auth.currentUser) {
    const idToken = await auth.currentUser.getIdToken();
    headers['Authorization'] = `Bearer ${idToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'API request failed');
  }

  return response.json();
}
```

### 査定 API の呼び出し

```typescript
// lib/appraisal.ts
import { apiRequest } from './api';

export interface AnalyzeRequest {
  image_base64: string;
  user_comment?: string;
  platform?: 'web' | 'ios' | 'android';
}

export interface AnalyzeResponse {
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

export async function analyzeImage(
  request: AnalyzeRequest
): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>('/api/v1/analyze', {
    method: 'POST',
    body: request,
    requireAuth: true,  // 履歴保存のため認証必須
  });
}

// 認証なしで査定のみ実行する場合
export async function analyzeImageWithoutAuth(
  request: AnalyzeRequest
): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>('/api/v1/analyze', {
    method: 'POST',
    body: request,
    requireAuth: false,
  });
}
```

## React コンポーネント例

### 査定フォーム

```tsx
// components/AppraisalForm.tsx
import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { analyzeImage, AnalyzeResponse } from '@/lib/appraisal';

export function AppraisalForm() {
  const { user, loading: authLoading, signInAsAnonymous } = useAuth();
  const [image, setImage] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleImageChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      setImage(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!image) return;

    setLoading(true);
    setError(null);

    try {
      // 未認証なら匿名サインイン
      if (!user) {
        await signInAsAnonymous();
      }

      const response = await analyzeImage({
        image_base64: image,
        platform: 'web',
      });

      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : '査定に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  if (authLoading) {
    return <div>認証中...</div>;
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="file"
        accept="image/*"
        onChange={handleImageChange}
        disabled={loading}
      />

      {image && (
        <img src={image} alt="Preview" style={{ maxWidth: 300 }} />
      )}

      <button type="submit" disabled={!image || loading}>
        {loading ? '査定中...' : '査定する'}
      </button>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      {result && <AppraisalResult result={result} />}
    </form>
  );
}
```

### 査定結果の表示

```tsx
// components/AppraisalResult.tsx
import { AnalyzeResponse } from '@/lib/appraisal';

interface Props {
  result: AnalyzeResponse;
}

export function AppraisalResult({ result }: Props) {
  // 既製品の場合
  if (result.classification === 'mass_product' && result.price) {
    return (
      <div className="result">
        <h2>{result.identified_product || result.item_name}</h2>

        <div className="price-range">
          <span className="label">中古相場</span>
          <span className="value">
            {result.price.min_price.toLocaleString()}円 〜{' '}
            {result.price.max_price.toLocaleString()}円
          </span>
        </div>

        <p className="message">{result.price.display_message}</p>

        {result.price_factors && result.price_factors.length > 0 && (
          <div className="factors">
            <h3>価格に影響する要因</h3>
            <ul>
              {result.price_factors.map((factor, i) => (
                <li key={i}>{factor}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="confidence">
          <span className={`badge ${result.confidence?.level}`}>
            信頼度: {result.confidence?.level}
          </span>
          <p>{result.confidence?.reasoning}</p>
        </div>

        <div className="features">
          {result.visual_features.map((feature, i) => (
            <span key={i} className="tag">{feature}</span>
          ))}
        </div>
      </div>
    );
  }

  // 一点物の場合
  if (result.classification === 'unique_item') {
    return (
      <div className="result unique">
        <h2>{result.item_name}</h2>
        <p className="message">{result.message}</p>
        <p className="recommendation">{result.recommendation}</p>
      </div>
    );
  }

  // 査定不可の場合
  return (
    <div className="result error">
      <p className="message">{result.message}</p>
      {result.retry_advice && (
        <p className="advice">{result.retry_advice}</p>
      )}
    </div>
  );
}
```

## トークンの自動更新

Firebase ID Token は1時間で期限切れになります。
`getIdToken()` は自動的に期限切れトークンを更新しますが、
長時間のセッションでは明示的に更新することを推奨します。

```typescript
// lib/api.ts
import { auth } from '@/lib/firebase';

// トークンを強制的に更新
export async function refreshToken(): Promise<string | null> {
  const user = auth.currentUser;
  if (!user) return null;

  try {
    // true を渡すと強制的に新しいトークンを取得
    return await user.getIdToken(true);
  } catch (error) {
    console.error('Token refresh failed:', error);
    return null;
  }
}
```

## 注意事項

1. **匿名ユーザーの永続性**
   - 匿名ユーザーはブラウザのローカルストレージに保存されます
   - ブラウザのデータをクリアすると、匿名ユーザーは失われます
   - 重要なデータは、アカウントのアップグレードを促してください

2. **セキュリティ**
   - ID Token は機密情報です。ログに出力しないでください
   - HTTPS 経由でのみ API を呼び出してください

3. **エラーハンドリング**
   - トークン期限切れ（401エラー）時は、トークンを更新して再試行してください
   - ネットワークエラー時は適切にユーザーに通知してください
