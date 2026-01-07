#!/usr/bin/env sh
#
# 開発用 Docker イメージをビルドして実行します。
#
# 使い方:
#   ./run.sh                    # FastAPI 開発サーバーを起動
#   ./run.sh hello              # CLI コマンドを実行
#   ./run.sh /bin/bash          # bash シェルに入る
#   ./run.sh uv sync --locked   # 環境の同期状態を確認

# Windows Git Bash のパス変換問題を回避（Mac/Linux では無視される）
export MSYS_NO_PATHCONV=1
if [ -t 1 ]; then
    INTERACTIVE="-it"
else
    INTERACTIVE=""
fi
docker run \
    --rm \
    --volume "$(pwd)":/app \
    --volume /app/.venv \
    --publish 8000:8000 \
    $INTERACTIVE \
    $(docker build -q .) \
    "$@"