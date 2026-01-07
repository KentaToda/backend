# 開発用 Dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# 非rootユーザーの作成
RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app

# uv の設定
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# /app ディレクトリの所有権を変更（ここは root で実行）
RUN chown nonroot:nonroot /app

# ここで nonroot に切り替え
USER nonroot

# 依存関係のインストール（キャッシュ最適化）
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# ソースコードをコピーしてインストール（--chown で所有権設定）
COPY --chown=nonroot:nonroot . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked
 
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT []

# 開発モードで起動
CMD ["uv", "run", "fastapi", "dev", "--host", "0.0.0.0", "src/backend"]