# UI 実装ガイドライン

## 概要

このドキュメントでは、査定結果をユーザーに分かりやすく表示するためのUI実装ガイドラインを提供します。

## 査定フロー

```
[画像選択] → [査定中...] → [結果表示]
```

---

## 画像選択コンポーネント

ユーザーが査定対象の画像を選択するためのコンポーネントです。
ファイル参照、ドラッグ&ドロップ、カメラ起動に対応します。

### UI レイアウト

```
┌─────────────────────────────────────────┐
│                                          │
│      ┌──────────────────────────┐       │
│      │                          │       │
│      │    📷 画像をドロップ      │       │
│      │    または                 │       │
│      │    [ファイルを選択]       │       │
│      │                          │       │
│      │  モバイル: [カメラで撮影]  │       │
│      │                          │       │
│      └──────────────────────────┘       │
│                                          │
│  対応形式: JPEG, PNG, WebP (最大10MB)    │
│                                          │
└─────────────────────────────────────────┘
```

### 実装例

```tsx
// components/ImagePicker.tsx
import { useState, useCallback, useRef } from 'react';

interface ImagePickerProps {
  onImageSelect: (base64: string) => void;
  disabled?: boolean;
}

export function ImagePicker({ onImageSelect, disabled }: ImagePickerProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  // モバイル判定
  const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

  const processFile = useCallback((file: File) => {
    // バリデーション
    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      alert('JPEG、PNG、WebP形式の画像を選択してください');
      return;
    }

    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      alert('ファイルサイズは10MB以下にしてください');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result as string;
      setPreview(base64);
      onImageSelect(base64);
    };
    reader.readAsDataURL(file);
  }, [onImageSelect]);

  // ドラッグ&ドロップ
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      processFile(file);
    }
  }, [processFile]);

  // ファイル選択
  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  }, [processFile]);

  // プレビューのクリア
  const handleClear = useCallback(() => {
    setPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (cameraInputRef.current) cameraInputRef.current.value = '';
  }, []);

  if (preview) {
    return (
      <div className="image-picker-preview">
        <img src={preview} alt="選択された画像" />
        <button onClick={handleClear} disabled={disabled}>
          別の画像を選択
        </button>
      </div>
    );
  }

  return (
    <div
      className={`image-picker ${isDragging ? 'dragging' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="image-picker-content">
        <span className="icon">📷</span>
        <p>画像をドロップ</p>
        <p className="or">または</p>

        <div className="buttons">
          {/* ファイル選択 */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileChange}
            disabled={disabled}
            hidden
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
          >
            ファイルを選択
          </button>

          {/* カメラ起動（モバイルのみ） */}
          {isMobile && (
            <>
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleFileChange}
                disabled={disabled}
                hidden
              />
              <button
                onClick={() => cameraInputRef.current?.click()}
                disabled={disabled}
                className="camera-button"
              >
                カメラで撮影
              </button>
            </>
          )}
        </div>
      </div>

      <p className="hint">対応形式: JPEG, PNG, WebP (最大10MB)</p>
    </div>
  );
}
```

### スタイル

```css
.image-picker {
  border: 2px dashed #E5E7EB;
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  transition: all 0.2s ease;
  background-color: #FAFAFA;
}

.image-picker.dragging {
  border-color: #3B82F6;
  background-color: #EFF6FF;
}

.image-picker-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.image-picker .icon {
  font-size: 48px;
}

.image-picker .or {
  color: #9CA3AF;
  font-size: 14px;
}

.image-picker .buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.image-picker button {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  background-color: #3B82F6;
  color: white;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.image-picker button:hover:not(:disabled) {
  background-color: #2563EB;
}

.image-picker button:disabled {
  background-color: #9CA3AF;
  cursor: not-allowed;
}

.image-picker .camera-button {
  background-color: #10B981;
}

.image-picker .camera-button:hover:not(:disabled) {
  background-color: #059669;
}

.image-picker .hint {
  color: #9CA3AF;
  font-size: 12px;
  margin-top: 16px;
}

/* プレビュー表示 */
.image-picker-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.image-picker-preview img {
  max-width: 100%;
  max-height: 300px;
  border-radius: 8px;
  object-fit: contain;
}
```

---

## 結果表示パターン

### 1. 既製品（mass_product）

最も一般的なケース。価格情報と価格変動要因を表示します。

```
┌─────────────────────────────────────────┐
│ NIKE Air Max 90, 白                      │
│                                          │
│ 中古相場                                  │
│ ¥8,000 〜 ¥15,000                        │
│                                          │
│ 📊 メルカリでの一般的な中古相場です        │
│                                          │
│ 💡 価格に影響する要因                     │
│ • 2020年以降のモデルは10000-15000円      │
│ • 箱・付属品ありで+1000-2000円           │
│ • 未使用品は15000-20000円               │
│                                          │
│ ✓ 信頼度: 高                             │
│   同一商品の取引実績が多数確認できました   │
│                                          │
│ タグ: [白] [スニーカー] [美品]            │
└─────────────────────────────────────────┘
```

**表示要素:**
- 商品名（`identified_product` または `item_name`）
- 価格範囲（`price.min_price` 〜 `price.max_price`）
- 表示メッセージ（`price.display_message`）
- 価格変動要因（`price_factors`）- ある場合のみ
- 信頼度（`confidence.level`）と理由（`confidence.reasoning`）
- 視覚的特徴（`visual_features`）

### 2. 一点物（unique_item）

価格算出ができない場合。専門家査定を推奨します。

```
┌─────────────────────────────────────────┐
│ 手作り陶芸 花瓶                          │
│                                          │
│ ⚠️ 一点物のため市場価格の算出が困難です   │
│                                          │
│ 💡 専門家による査定をお勧めします         │
│                                          │
│ 理由:                                    │
│ 市場に同一商品の流通が確認できませんでした │
│                                          │
│ タグ: [青い釉薬] [大型] [手作り感]        │
└─────────────────────────────────────────┘
```

**表示要素:**
- 商品名（`item_name`）
- メッセージ（`message`）
- 推奨アクション（`recommendation`）
- 判定理由（`confidence.reasoning`）
- 視覚的特徴（`visual_features`）

### 3. 査定不可（unknown）

画像から商品を特定できない場合。再撮影を促します。

```
┌─────────────────────────────────────────┐
│ ❌ 査定できませんでした                   │
│                                          │
│ 画像から商品を特定できませんでした        │
│                                          │
│ 📷 再撮影のアドバイス                     │
│ 明るい場所で商品全体が写るように          │
│ 撮影してください                         │
│                                          │
│ [もう一度撮影する]                        │
└─────────────────────────────────────────┘
```

**表示要素:**
- エラーメッセージ（`message`）
- 再撮影アドバイス（`retry_advice`）
- 再撮影ボタン

### 4. 禁止物（prohibited）

査定対象外の画像が送信された場合。

```
┌─────────────────────────────────────────┐
│ ⛔ この画像は査定対象外です              │
│                                          │
│ 商品のみが写った画像を使用してください    │
│                                          │
│ [別の画像を選択する]                      │
└─────────────────────────────────────────┘
```

## 信頼度の表示

信頼度に応じて視覚的なフィードバックを変更することを推奨します。

| level | 色 | アイコン | メッセージ例 |
|-------|-----|---------|-------------|
| high | 緑 (#10B981) | ✓ | 信頼度: 高 |
| medium | 黄 (#F59E0B) | △ | 信頼度: 中 |
| low | 赤 (#EF4444) | ! | 信頼度: 低 |

```css
.confidence-high {
  color: #10B981;
  background-color: #ECFDF5;
}

.confidence-medium {
  color: #F59E0B;
  background-color: #FFFBEB;
}

.confidence-low {
  color: #EF4444;
  background-color: #FEF2F2;
}
```

## 価格表示のフォーマット

```typescript
function formatPrice(price: number): string {
  return `¥${price.toLocaleString('ja-JP')}`;
}

function formatPriceRange(min: number, max: number): string {
  if (min === max) {
    return formatPrice(min);
  }
  return `${formatPrice(min)} 〜 ${formatPrice(max)}`;
}

// 使用例
formatPriceRange(8000, 15000);  // "¥8,000 〜 ¥15,000"
```

## ローディング状態（AI Thinking 表示）

査定中は、AIの思考プロセスをストリームで表示することで、ユーザーに処理の進行状況を伝えます。
折り畳み可能なコンポーネントで実装し、詳細を見たいユーザーのみ展開できるようにします。

### UI レイアウト

```
┌─────────────────────────────────────────┐
│  ⏳ 査定中...                            │
│                                          │
│  ▼ AIの分析プロセスを表示                │
│  ┌────────────────────────────────────┐ │
│  │ 🔍 画像を解析しています...          │ │
│  │ → 商品カテゴリ: スニーカー          │ │
│  │ → ブランド: NIKE を検出             │ │
│  │ → モデル特定中...                   │ │
│  │ 🌐 市場価格を検索しています...       │ │
│  │ → メルカリで取引実績を確認中        │ │
│  │ → 価格帯を分析中... █████░░░        │ │
│  └────────────────────────────────────┘ │
│                                          │
│  処理には10-30秒程度かかります           │
└─────────────────────────────────────────┘
```

### ストリーミングAPI の接続

バックエンドがSSE（Server-Sent Events）でthinkingを配信する場合の実装例です。

```typescript
// lib/streaming.ts
export interface ThinkingEvent {
  type: 'thinking' | 'progress' | 'complete' | 'error';
  node?: 'vision' | 'search' | 'price';
  message: string;
  timestamp: number;
}

export function createThinkingStream(
  imageBase64: string,
  token?: string,
  onThinking: (event: ThinkingEvent) => void,
  onComplete: (result: AnalyzeResponse) => void,
  onError: (error: Error) => void
): () => void {
  const controller = new AbortController();

  const fetchStream = async () => {
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch('/api/v1/analyze/stream', {
        method: 'POST',
        headers,
        body: JSON.stringify({ image_base64: imageBase64 }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error('API request failed');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));

            if (data.type === 'complete') {
              onComplete(data.result);
            } else if (data.type === 'error') {
              onError(new Error(data.message));
            } else {
              onThinking(data);
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        onError(error);
      }
    }
  };

  fetchStream();

  // クリーンアップ関数
  return () => controller.abort();
}
```

### コンポーネント実装

```tsx
// components/AnalysisProgress.tsx
import { useState, useEffect, useRef } from 'react';
import { ThinkingEvent } from '@/lib/streaming';

interface AnalysisProgressProps {
  isLoading: boolean;
  thinkingEvents: ThinkingEvent[];
}

export function AnalysisProgress({ isLoading, thinkingEvents }: AnalysisProgressProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 新しいイベントが追加されたら自動スクロール
  useEffect(() => {
    if (scrollRef.current && isExpanded) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [thinkingEvents, isExpanded]);

  if (!isLoading && thinkingEvents.length === 0) {
    return null;
  }

  const getNodeIcon = (node?: string) => {
    switch (node) {
      case 'vision': return '👁️';
      case 'search': return '🔍';
      case 'price': return '💰';
      default: return '🤖';
    }
  };

  const getNodeLabel = (node?: string) => {
    switch (node) {
      case 'vision': return '画像解析';
      case 'search': return '商品検索';
      case 'price': return '価格調査';
      default: return '処理中';
    }
  };

  return (
    <div className="analysis-progress">
      {/* ヘッダー */}
      <div className="progress-header">
        {isLoading && <span className="spinner" />}
        <span className="status">
          {isLoading ? '査定中...' : '分析完了'}
        </span>
      </div>

      {/* 折り畳みトグル */}
      <button
        className="toggle-button"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
      >
        <span className={`arrow ${isExpanded ? 'expanded' : ''}`}>▶</span>
        AIの分析プロセスを{isExpanded ? '非表示' : '表示'}
      </button>

      {/* Thinking コンテンツ */}
      {isExpanded && (
        <div className="thinking-container" ref={scrollRef}>
          {thinkingEvents.map((event, index) => (
            <div key={index} className={`thinking-item ${event.type}`}>
              <span className="node-icon">{getNodeIcon(event.node)}</span>
              <div className="thinking-content">
                {event.node && (
                  <span className="node-label">{getNodeLabel(event.node)}</span>
                )}
                <span className="message">{event.message}</span>
              </div>
              <span className="timestamp">
                {new Date(event.timestamp).toLocaleTimeString('ja-JP', {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })}
              </span>
            </div>
          ))}

          {/* 処理中のインジケーター */}
          {isLoading && (
            <div className="thinking-item pending">
              <span className="node-icon">⏳</span>
              <span className="message typing-indicator">
                <span></span><span></span><span></span>
              </span>
            </div>
          )}
        </div>
      )}

      {/* フッター */}
      {isLoading && (
        <p className="hint">処理には10-30秒程度かかります</p>
      )}
    </div>
  );
}
```

### 使用例

```tsx
// pages/appraisal.tsx
import { useState, useCallback } from 'react';
import { ImagePicker } from '@/components/ImagePicker';
import { AnalysisProgress } from '@/components/AnalysisProgress';
import { AppraisalResult } from '@/components/AppraisalResult';
import { createThinkingStream, ThinkingEvent } from '@/lib/streaming';
import { useAuth } from '@/hooks/useAuth';

export default function AppraisalPage() {
  const { getIdToken } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingEvents, setThinkingEvents] = useState<ThinkingEvent[]>([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState<string | null>(null);

  const handleImageSelect = useCallback(async (base64: string) => {
    setIsLoading(true);
    setThinkingEvents([]);
    setResult(null);
    setError(null);

    const token = await getIdToken();

    createThinkingStream(
      base64,
      token ?? undefined,
      // onThinking
      (event) => {
        setThinkingEvents((prev) => [...prev, event]);
      },
      // onComplete
      (data) => {
        setResult(data);
        setIsLoading(false);
      },
      // onError
      (err) => {
        setError(err.message);
        setIsLoading(false);
      }
    );
  }, [getIdToken]);

  return (
    <div className="appraisal-page">
      <h1>商品を査定する</h1>

      <ImagePicker
        onImageSelect={handleImageSelect}
        disabled={isLoading}
      />

      <AnalysisProgress
        isLoading={isLoading}
        thinkingEvents={thinkingEvents}
      />

      {error && (
        <div className="error-message">{error}</div>
      )}

      {result && (
        <AppraisalResult result={result} />
      )}
    </div>
  );
}
```

### スタイル

```css
/* 分析プログレス */
.analysis-progress {
  margin: 24px 0;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 16px;
  background-color: #FAFAFA;
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.progress-header .spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #E5E7EB;
  border-top-color: #3B82F6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-header .status {
  font-weight: 600;
  font-size: 16px;
}

/* トグルボタン */
.toggle-button {
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  color: #6B7280;
  cursor: pointer;
  font-size: 14px;
  padding: 8px 0;
}

.toggle-button:hover {
  color: #3B82F6;
}

.toggle-button .arrow {
  transition: transform 0.2s ease;
  font-size: 10px;
}

.toggle-button .arrow.expanded {
  transform: rotate(90deg);
}

/* Thinking コンテナ */
.thinking-container {
  max-height: 300px;
  overflow-y: auto;
  margin: 12px 0;
  padding: 12px;
  background-color: #1F2937;
  border-radius: 8px;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
  font-size: 13px;
}

.thinking-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
  color: #E5E7EB;
  border-bottom: 1px solid #374151;
}

.thinking-item:last-child {
  border-bottom: none;
}

.thinking-item .node-icon {
  flex-shrink: 0;
}

.thinking-item .thinking-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.thinking-item .node-label {
  color: #60A5FA;
  font-weight: 500;
  font-size: 11px;
}

.thinking-item .message {
  color: #D1D5DB;
}

.thinking-item.progress .message {
  color: #FCD34D;
}

.thinking-item .timestamp {
  color: #6B7280;
  font-size: 11px;
  flex-shrink: 0;
}

/* タイピングインジケーター */
.typing-indicator {
  display: flex;
  gap: 4px;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  background-color: #60A5FA;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
.typing-indicator span:nth-child(3) { animation-delay: 0s; }

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* ヒント */
.analysis-progress .hint {
  color: #9CA3AF;
  font-size: 12px;
  margin-top: 12px;
  text-align: center;
}

/* カスタムスクロールバー */
.thinking-container::-webkit-scrollbar {
  width: 6px;
}

.thinking-container::-webkit-scrollbar-track {
  background: #374151;
  border-radius: 3px;
}

.thinking-container::-webkit-scrollbar-thumb {
  background: #6B7280;
  border-radius: 3px;
}

.thinking-container::-webkit-scrollbar-thumb:hover {
  background: #9CA3AF;
}
```

### ノード別メッセージ例

各ノードからのthinkingメッセージの例です。

| ノード | メッセージ例 |
|--------|-------------|
| vision | `画像を解析しています...` |
| vision | `商品カテゴリ: スニーカー を検出` |
| vision | `ブランド: NIKE の可能性が高いです` |
| search | `商品名で市場を検索しています...` |
| search | `メルカリで取引実績を確認中` |
| search | `同一商品を 15 件発見しました` |
| price | `価格帯を分析しています...` |
| price | `直近3ヶ月の取引価格を集計中` |
| price | `価格変動要因を特定しました` |

### 非ストリーミング時のフォールバック

ストリーミングAPIが利用できない場合のシンプルなローディング表示です。

```tsx
function SimpleLoadingState() {
  return (
    <div className="simple-loading">
      <div className="spinner" />
      <p>画像を分析中...</p>
      <div className="progress-steps">
        <span className="step active">画像解析</span>
        <span className="step">商品検索</span>
        <span className="step">価格調査</span>
      </div>
      <p className="hint">処理には10-30秒程度かかります</p>
    </div>
  );
}
```

## エラーハンドリング

### ネットワークエラー

```tsx
function NetworkError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="error">
      <p>通信エラーが発生しました</p>
      <p>ネットワーク接続を確認してください</p>
      <button onClick={onRetry}>再試行</button>
    </div>
  );
}
```

### 認証エラー

```tsx
function AuthError({ onReauth }: { onReauth: () => void }) {
  return (
    <div className="error">
      <p>セッションが切れました</p>
      <button onClick={onReauth}>再ログイン</button>
    </div>
  );
}
```

## 履歴一覧の表示

```
┌─────────────────────────────────────────┐
│ 📋 査定履歴                              │
├─────────────────────────────────────────┤
│ [画像] NIKE Air Max 90         ¥8,000〜 │
│        1月11日 12:34                     │
├─────────────────────────────────────────┤
│ [画像] Louis Vuitton ネヴァーフル  一点物 │
│        1月10日 15:20                     │
├─────────────────────────────────────────┤
│ [画像] SEIKO プレザージュ      ¥35,000〜 │
│        1月9日 09:15                      │
└─────────────────────────────────────────┘
```

```tsx
function AppraisalHistoryItem({ appraisal }: { appraisal: AppraisalDocument }) {
  const displayName = appraisal.search?.identified_product
    || appraisal.vision.item_name
    || '不明な商品';

  const priceDisplay = appraisal.price
    ? `¥${appraisal.price.min_price.toLocaleString()}〜`
    : appraisal.search?.classification === 'unique_item'
      ? '一点物'
      : '査定不可';

  const date = appraisal.created_at.toDate();
  const dateStr = date.toLocaleDateString('ja-JP', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className="history-item">
      <div className="thumbnail">
        {/* サムネイル画像 */}
      </div>
      <div className="info">
        <p className="name">{displayName}</p>
        <p className="date">{dateStr}</p>
      </div>
      <div className="price">{priceDisplay}</div>
    </div>
  );
}
```

## アクセシビリティ

1. **色だけに頼らない**: 信頼度をアイコンとテキストでも表示
2. **適切なコントラスト**: WCAG 2.1 AA 基準を満たす
3. **フォーカス管理**: キーボード操作でアクセス可能に
4. **alt テキスト**: 画像には適切な説明を付与

```tsx
<img
  src={imageUrl}
  alt={`${itemName}の査定画像`}
/>

<span className="confidence-high" role="status">
  <CheckIcon aria-hidden="true" />
  信頼度: 高
</span>
```

## レスポンシブデザイン

- モバイル: 縦に積み上げるレイアウト
- タブレット: 2カラムレイアウト
- デスクトップ: サイドバー付きレイアウト

```css
/* モバイル優先 */
.result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* タブレット以上 */
@media (min-width: 768px) {
  .result {
    flex-direction: row;
  }

  .result-main {
    flex: 2;
  }

  .result-sidebar {
    flex: 1;
  }
}
```
