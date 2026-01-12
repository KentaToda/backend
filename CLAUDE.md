# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ojoya is an AI-powered product appraisal backend that analyzes product images and provides market valuations. Built with FastAPI and LangGraph, it implements a multi-step AI agent pipeline using Google Gemini 2.5 Flash.

## Development Commands

```bash
# Install dependencies (using uv package manager)
uv sync --locked

# Run development server
fastapi dev src/backend/main.py

# Run with Docker
docker compose up dev        # Development
docker compose up prod       # Production

# Linting
ruff check .
ruff format .

# Testing
pytest
```

## Environment Setup

Copy `.env.example` to `.env` and configure:
- `GCP_PROJECT_ID` / `GCP_LOCATION` - Google Cloud settings
- `MODEL_VISION_NODE` / `MODEL_SEARCH_NODE` - Gemini model names
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON (local dev only)
- `CORS_ORIGINS` - Allowed frontend origins

## Architecture

### LangGraph Agent Pipeline

The core workflow is defined in `src/backend/features/agent/graph.py`:

```
Image Input → Vision Node → (if processable) → Search Node → (if mass_product) → Price Node
```

**Three processing nodes:**
1. **Vision Node** (`features/agent/vision/`): Classifies images as `processable`, `unknown`, or `prohibited`. Extracts item name and visual features.
2. **Search Node** (`features/agent/search/`): Performs image search, classifies as `mass_product` (standard goods) or `unique_item` (one-of-a-kind).
3. **Price Node** (`features/agent/price/`): Calculates market valuation with min/max prices and confidence levels.

Each node has its own schema definitions in `schema.py` and implementation in `node.py`.

### Key Directories

```
src/backend/
├── api/v1/endpoints/     # FastAPI route handlers
├── core/                 # Config, Firebase, Firestore, logging utilities
└── features/agent/       # LangGraph nodes and state management
```

### API Endpoints

- `POST /api/v1/analyze` - Main analysis endpoint (accepts base64 image)
- `GET /api/v1/appraisals/{id}` - Get appraisal history
- `GET /api/v1/health` - Health check

### State Management

Agent state is defined in `features/agent/state.py` using TypedDict. State flows through nodes carrying:
- `messages` - LangChain message history
- `retry_count` - Retry attempts for unknown images
- `analysis_result` - Vision node output
- `search_output` - Search node output
- `price_output` - Price node output

## Code Patterns

- **Async everywhere**: All handlers and LangGraph nodes use async/await
- **Structured LLM output**: Nodes use `.with_structured_output()` with Pydantic models
- **Firebase Auth**: Optional Bearer token authentication via Firebase Admin SDK
- **Firestore**: User and appraisal data storage with async operations
- **Cloud Logging**: JSON-formatted logs in production, human-readable in development

## Agent Design Decisions

From `docs/agent.md`:
- Max 5 retry attempts for `unknown` image classifications
- Max 2 follow-up questions to users for incomplete valuations
- "Upside potential" hints when full valuation isn't possible (e.g., "if this is a first edition, value could be 150,000 JPY")
- Prohibited items (faces, animals, cash, cards) are rejected immediately
