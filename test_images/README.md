# Test Images

このディレクトリはVision Agentのテスト用画像を配置する場所です。

## 使用方法

1. テスト用の画像ファイル（jpg, png等）をこのディレクトリに配置
2. APIリクエスト時に `file_path` で相対パスを指定

### リクエスト例

```json
{
  "file_path": "test_images/sample.jpg"
}
```

## Dockerコンテナ内のパス

- ローカル: `backend/test_images/`
- コンテナ内: `/app/test_images/`

## 注意事項

- 本番環境では使用しないでください
- 大きなファイルはGit管理から除外することを推奨します
