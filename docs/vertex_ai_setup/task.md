# Vertex AI 接続計画

- [ ] 事前準備
    - [ ] Google Cloud Project ID の確認
    - [ ] **(重要) 課金の有効化** (Google Cloud Consoleの「お支払い」で設定)
    - [ ] Vertex AI API の有効化
    - [ ] サービスアカウントの作成とキー(JSON)のダウンロード
    - [x] キーファイルをプロジェクトルートに配置 (`google_credentials.json`)
- [ ] 設定変更
    - [x] `.gitignore` にキーファイルを追加
    - [x] `compose.yaml` に環境変数とボリュームマウントを追加
- [ ] 接続確認
    - [x] 接続テスト用スクリプトの作成 (`src/backend/test_vertex.py`)
    - [ ] Docker経由でのスクリプト実行と動作確認
