# Vertex AI 接続実装計画

## 目標
Docker環境上で、サービスアカウントを使用してVertex AIへの接続を確認します。

## 事前準備 (ユーザー作業)
1.  **課金の有効化 [重要]**: Google Cloud Consoleでプロジェクトへの課金を有効にしてください。Vertex AI を使用するには課金設定が必須です。
2.  **APIの有効化**: Google Cloud Consoleで「Vertex AI API」を有効にしてください。
3.  **サービスアカウント**:
    - IAM管理画面で新しいサービスアカウントを作成するか、既存のものを使用します。
    - 「Vertex AI ユーザー」などの適切なロールを付与します。
    - キーを「JSON」形式で作成し、ダウンロードします。
    - ファイルを `google_credentials.json` という名前で `backend` フォルダの直下に配置してください。

## 変更内容
### 設定ファイル
#### [MODIFY] [backend/.gitignore](file:///c:/src/personal/ojoya/backend/.gitignore)
- `google_credentials.json` を追記して、認証情報がコミットされないようにします。

#### [MODIFY] [backend/compose.yaml](file:///c:/src/personal/ojoya/backend/compose.yaml)
- `environment` に `GOOGLE_APPLICATION_CREDENTIALS=/app/google_credentials.json` を追加します。

### Backend
#### [NEW] [src/backend/test_vertex.py](file:///c:/src/personal/ojoya/backend/src/backend/test_vertex.py)
以下の動作を行うシンプルなスクリプトを作成します:
1.  `langchain-google-vertexai` を使用して Vertex AI を初期化。
2.  `gemini-1.5-flash` モデルに「Hello」というプロンプトを送信。
3.  応答を表示。

## 検証計画
### 自動テスト
Docker環境内でスクリプトを実行します:
```powershell
docker compose run --rm dev uv run src/backend/test_vertex.py
```
