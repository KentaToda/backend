# Ojoya Backend - Google Cloud Run デプロイ計画

## 概要

FastAPI + LangGraph バックエンドを Google Cloud Run にデプロイする手順書です。
**GCPコンソール（Web UI）をメインに使用**します。

- **GCPプロジェクト**: `ojoya-483609`（作成済み）
- **デプロイ先**: Cloud Run（手動デプロイ）
- **リージョン**: `asia-northeast1`（東京）

---

## アーキテクチャ

### フロントエンド配信方式

フロントエンド（React + TypeScript）は FastAPI の静的ファイル配信機能で提供されます。

```
┌─────────────────────────────────────────────────────────┐
│                    Cloud Run                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │                  FastAPI                          │  │
│  │                                                   │  │
│  │  /api/v1/*  →  APIエンドポイント                  │  │
│  │  /*         →  frontend/dist/ 静的ファイル配信    │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Dockerビルドプロセス（マルチステージ）

```
dockerfile.prod
├── Stage 1: frontend-builder (Node.js)
│   └── npm ci && npm run build → /frontend/dist
├── Stage 2: builder (Python/uv)
│   └── uv sync → Python依存関係
└── Stage 3: 本番イメージ (Debian slim)
    ├── /app (Pythonアプリ)
    └── /app/frontend/dist (ビルド済みフロントエンド)
```

---

## Step 1: GCP APIの有効化

### 1.1 GCPコンソールにアクセス

https://console.cloud.google.com/ にログイン

### 1.2 プロジェクト選択

画面上部のプロジェクトセレクターで `ojoya-483609` を選択

### 1.3 必要なAPIを有効化

左メニュー > 「APIとサービス」 > 「ライブラリ」で以下を検索して有効化：

| API名 | 用途 |
|-------|------|
| Cloud Run Admin API | Cloud Runサービス管理 |
| Cloud Build API | Dockerイメージビルド |
| Artifact Registry API | Dockerイメージ保存 |
| Vertex AI API | Gemini 2.5 Flash |
| Cloud Firestore API | データベース |
| Firebase Management API | Firebase連携 |

各APIを検索 → 「有効にする」ボタンをクリック

---

## Step 2: Firebase/Firestoreセットアップ

### 2.1 FirebaseをGCPプロジェクトに追加

1. https://console.firebase.google.com/ にアクセス
2. 「プロジェクトを追加」をクリック
3. 既存のGCPプロジェクト `ojoya-483609` を選択
4. Google Analyticsは任意（スキップ可）
5. 「Firebaseを追加」をクリック

### 2.2 Firestoreデータベース作成

Firebase Console内で：
1. 左メニュー > 「Firestore Database」
2. 「データベースを作成」をクリック
3. **本番モード**を選択
4. ロケーション: `asia-northeast1（東京）` を選択
5. 「有効にする」をクリック

### 2.3 Firebase Authentication設定

Firebase Console内で：
1. 左メニュー > 「Authentication」
2. 「始める」をクリック
3. 「Sign-in method」タブで必要な認証方法を有効化：
   - 匿名（Anonymous）- ゲストユーザー用
   - メール/パスワード - 登録ユーザー用

### 2.4 Firestoreセキュリティルール設定

Firebase Console > Firestore > 「ルール」タブで以下を入力して公開：

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
      match /appraisals/{appraisalId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
    }
  }
}
```

---

## Step 3: サービスアカウント設定

### 3.1 サービスアカウント作成

GCPコンソール > 「IAMと管理」 > 「サービスアカウント」：

1. 「サービスアカウントを作成」をクリック
2. 名前: `ojoya-backend-sa`
3. 説明: `Ojoya Backend Service Account`
4. 「作成して続行」をクリック

### 3.2 ロール付与

同じ画面で以下のロールを追加：

| ロール | 用途 |
|--------|------|
| Vertex AI ユーザー | Gemini APIアクセス |
| Cloud Datastore ユーザー | Firestoreアクセス |
| Firebase Admin SDK 管理サービス エージェント | Firebase認証 |

5. 「完了」をクリック

### 3.3 ユーザーアカウントへの権限付与

Cloud Build を実行するユーザーアカウントに権限を付与：

GCPコンソール > 「IAMと管理」 > 「IAM」：

1. 「アクセス権を付与」をクリック
2. 新しいプリンシパル: `your-email@gmail.com`
3. 以下のロールを追加：
   - Cloud Build 編集者 (roles/cloudbuild.builds.editor)
   - Artifact Registry 書き込み (roles/artifactregistry.writer)
4. 「保存」をクリック

---

## Step 4: Artifact Registry設定

### 4.1 リポジトリ作成

GCPコンソール > 「Artifact Registry」：

1. 「リポジトリを作成」をクリック
2. 名前: `ojoya`
3. 形式: `Docker`
4. モード: `標準`
5. ロケーション: `asia-northeast1（東京）`
6. 「作成」をクリック

---

## Step 5: Cloud Shellでビルド＆デプロイ

ここからはCloud Shell（ブラウザ内ターミナル）を使用します。

### 5.1 Cloud Shellを起動

GCPコンソール右上の `>_` アイコンをクリック → Cloud Shellが開く

### 5.2 ソースコードをアップロード

#### 方法A: ZIPファイルでアップロード（推奨）

1. ローカルPCで `ojoya` フォルダ全体をZIP圧縮
2. Cloud Shell右上の「︙」メニュー > 「アップロード」
3. ZIPファイルを選択してアップロード
4. 展開：

```bash
cd ~
unzip ojoya.zip
cd ojoya
```

#### 方法B: GitHubにリポジトリがある場合

```bash
git clone https://github.com/your-username/ojoya.git
cd ojoya
```

### 5.3 Cloud Buildでビルド＆プッシュ

```bash
# プロジェクト設定
gcloud config set project ojoya-483609

# プロジェクトルートからビルド（frontendのコピー不要）
gcloud builds submit --config=backend/cloudbuild.yaml
```

**ビルドプロセスの流れ:**

1. `cloudbuild.yaml` がプロジェクトルートから `dockerfile.prod` を使用してビルド開始
2. **Stage 1**: Node.js で `frontend/` をビルド（`npm run build` → `dist/` 生成）
3. **Stage 2**: `backend/` のPython依存関係をインストール
4. **Stage 3**: 本番イメージに `dist/` のみをコピー（ソースは含まない）

**注意**:
- `dockerfile.prod` は `--mount` オプションを使用しているため、BuildKit が必要です
- `cloudbuild.yaml` で BuildKit を有効化しています
- フロントエンドのビルドはDocker内で行われるため、ローカルでの事前ビルドは不要です
- **frontendを手動でコピーする必要はありません**（プロジェクトルートからビルドするため）

### 5.4 Cloud Runへデプロイ

```bash
gcloud run deploy ojoya-backend \
  --image=asia-northeast1-docker.pkg.dev/ojoya-483609/ojoya/api:latest \
  --region=asia-northeast1 \
  --platform=managed \
  --service-account=ojoya-backend-sa@ojoya-483609.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --port=8000 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --timeout=300 \
  --set-env-vars="GCP_PROJECT_ID=ojoya-483609" \
  --set-env-vars="GCP_LOCATION=us-central1" \
  --set-env-vars="MODEL_VISION_NODE=gemini-2.5-flash" \
  --set-env-vars="MODEL_SEARCH_NODE=gemini-2.5-flash" \
  --set-env-vars="ENVIRONMENT=production" \
  --set-env-vars="LOG_LEVEL=INFO" \
  --set-env-vars="CORS_ORIGINS=https://your-frontend-domain.com"
```

デプロイ完了後、サービスURLが表示されます（例: `https://ojoya-backend-xxxxx-an.a.run.app`）

---

## Step 6: デプロイ確認

### 6.1 GCPコンソールで確認

GCPコンソール > 「Cloud Run」：
- `ojoya-backend` サービスが表示される
- ステータスが「緑のチェック」になっていることを確認

### 6.2 ヘルスチェック

Cloud Shellまたはブラウザで：
```bash
curl https://ojoya-backend-xxxxx-an.a.run.app/api/v1/health
```

応答例：`{"status": "healthy"}`

### 6.3 フロントエンド確認

ブラウザでサービスURLのルートにアクセス：
```
https://ojoya-backend-xxxxx-an.a.run.app/
```

フロントエンドのHTMLが表示されることを確認。

---

## 設定値の説明

| パラメータ | 値 | 理由 |
|-----------|-----|------|
| `--memory=512Mi` | 512MB | LangGraph + Gemini呼び出しに十分 |
| `--min-instances=0` | 0 | コスト最適化（使用しない時はゼロに） |
| `--timeout=300` | 5分 | LLM呼び出しに余裕を持たせる |
| `--allow-unauthenticated` | 許可 | APIレベルでFirebase認証を処理 |

---

## 再デプロイ手順（クイックリファレンス）

Cloud Shellで：
```bash
# プロジェクトルートに移動
cd ~/ojoya

# ビルド＆プッシュ（frontendのコピー不要）
gcloud builds submit --config=backend/cloudbuild.yaml

# デプロイ
gcloud run deploy ojoya-backend \
  --image=asia-northeast1-docker.pkg.dev/ojoya-483609/ojoya/api:latest \
  --region=asia-northeast1
```

---

## サービス管理

### 一時停止（トラフィックを0%にする）

```bash
gcloud run services update-traffic ojoya-backend \
  --region=asia-northeast1 \
  --to-revisions=LATEST=0
```

### 再開（トラフィックを100%に戻す）

```bash
gcloud run services update-traffic ojoya-backend \
  --region=asia-northeast1 \
  --to-revisions=LATEST=100
```

### サービス削除

```bash
gcloud run services delete ojoya-backend --region=asia-northeast1
```

### 削除後の再デプロイ

イメージは Artifact Registry に残っているため、Step 5.4 のデプロイコマンドを再実行すればOK。
**注意**: サービスURLは削除前と異なる可能性があります。

---

## 検証方法

1. **ヘルスチェック**: ブラウザで `https://[サービスURL]/api/v1/health` にアクセス
2. **フロントエンド**: ブラウザで `https://[サービスURL]/` にアクセス
3. **ログ確認**: GCPコンソール > Cloud Run > ojoya-backend > ログ
4. **分析テスト**: Postman等でBase64画像を送信

---

## トラブルシューティング

### PERMISSION_DENIED エラー

Cloud Build 実行時に権限エラーが出る場合：
- Step 3.3 のユーザーアカウント権限付与を確認

### BuildKit エラー（`--mount option requires BuildKit`）

`gcloud builds submit --tag ...` ではなく、`cloudbuild.yaml` を使用：
```bash
gcloud builds submit --config=cloudbuild.yaml
```

### フロントエンドが表示されない

- Cloud Build ログで以下を確認：
  - Stage 1 (frontend-builder) が成功しているか
  - `npm run build` が正常に完了しているか
  - `dist/` ディレクトリが生成されているか
- プロジェクトルートから `gcloud builds submit` を実行しているか確認

### フロントエンドのビルドが失敗する

- `frontend/package.json` と `frontend/package-lock.json` が存在するか確認
- Node.js の依存関係エラーの場合は、ローカルで `npm ci && npm run build` を試して問題を特定

### 「404 Not Found」が表示される

- FastAPI が `/app/frontend/dist/` を検出できていない可能性
- Cloud Run のログで `FRONTEND_DIST_DIR` のパスを確認
- Dockerfile で `COPY --from=frontend-builder` が正しく実行されているか確認

---

## フロントエンド環境変数

フロントエンドのビルド時に以下の環境変数が必要です。
`frontend/.env.local` を作成するか、CI/CD で設定してください。

```env
VITE_FIREBASE_API_KEY=your-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_API_BASE_URL=  # 本番では空（同一オリジン）
```

**注意**: 本番ビルドでは `VITE_API_BASE_URL` は空にします（FastAPI と同一オリジンで配信されるため）。
