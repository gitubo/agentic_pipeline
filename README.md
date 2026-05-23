# ETCS Agentic Pipeline

LangGraph-based agentic pipeline for the automatic generation of ETCS Level 2 message sequences (Subset-026 v3.6.0) from natural-language descriptions.

## How it works

```
NL Input → [normalize] → [cache_lookup] → [plan] → [validate_formal]
                                                          ↓ retry ×3
                                                     [check_plausibility]
                                                          ↓ retry ×3
                                                     [instantiate] → [format_output]
```

The LLM is used only in the `normalize` and `plan` nodes. Validation, plausibility checking, and instantiation are fully deterministic and testable without an API key.

---

## Prerequisites

| Tool | Min version | Notes |
|------|-------------|-------|
| Python | 3.11+ | |
| [uv](https://docs.astral.sh/uv/) | any | package manager |
| PostgreSQL | 15+ | with `pgvector` extension |

### Install pgvector on PostgreSQL

```sql
-- connect as superuser and install the extension
CREATE EXTENSION IF NOT EXISTS vector;
```

Quick alternative with Docker:

```bash
docker run -d \
  --name etcs-pg \
  -e POSTGRES_USER=pipeline_user \
  -e POSTGRES_PASSWORD=changeme \
  -e POSTGRES_DB=pipeline_db \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

---

## Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd agentic_pipeline

# 2. Install dependencies with uv
uv sync

# 3. Copy and configure environment variables
cp .env.example .env
# then edit .env with your credentials (see Configuration section)
```

---

## Configuration

Open `.env` and set your LLM provider, API key, and database credentials.

### Example with OpenAI

```dotenv
# ── LLM ──────────────────────────────────────────────────────────
LLM_PROVIDER=openai
LLM_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS_PLANNER=4000
LLM_MAX_TOKENS_NORMALIZER=1000

# ── Embedding (local, no API key needed) ─────────────────────────
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIM=384

# ── Database ─────────────────────────────────────────────────────
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pipeline_db
DB_USER=pipeline_user
DB_PASSWORD=changeme
DB_SCHEMA=pipeline

# ── Profile ──────────────────────────────────────────────────────
PROFILES_ROOT=./profiles
ACTIVE_PROFILE=etcs

# ── Pipeline ─────────────────────────────────────────────────────
MAX_RERUN_FORMAL_VALIDATOR=3
MAX_RERUN_PLAUSIBILITY=3

# ── RAG ──────────────────────────────────────────────────────────
RAG_CHUNK_SIZE=512
RAG_CHUNK_OVERLAP=64
RAG_TOP_K=5

# ── Cache ────────────────────────────────────────────────────────
CACHE_TOP_K=3
CACHE_SIMILARITY_THRESHOLD=0.75

# ── Logging ──────────────────────────────────────────────────────
LOG_LEVEL=INFO
```

### Example with Anthropic (Claude)

```dotenv
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_MODEL=claude-sonnet-4-20250514
```

### Example with OpenAI-compatible provider (Ollama, Groq, Azure…)

```dotenv
LLM_PROVIDER=openai_compatible
LLM_API_KEY=gsk_xxxxxxxx          # Groq API key (or your provider's key)
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-70b-versatile
```

---

## First run — RAG indexing

Before running the pipeline, index the ETCS specification into the vector store:

```bash
uv run etcs-pipeline index
```

This populates PostgreSQL with Subset-026 spec chunks needed for retrieval during planning. Run this **once** (or whenever the spec changes). Use `--force` to reindex from scratch.

```bash
uv run etcs-pipeline index --force
```

---

## Running the pipeline

```bash
# Standard MA in FS mode at 200 km/h
uv run etcs-pipeline run "standard MA at 200 km/h, FS mode"

# Save output to a JSON file
uv run etcs-pipeline run "standard MA at 200 km/h, FS mode" --output output.json

# Emergency stop
uv run etcs-pipeline run "immediate emergency stop"

# Session establishment
uv run etcs-pipeline run "establish RBC session, then MA with two sections and gradient"
```

The output is a JSON containing the instantiated ETCS message sequence and pipeline metadata (nodes traversed, validation errors corrected, cache hit/miss).

### Adding a validated output to the semantic cache

```bash
uv run etcs-pipeline cache add output.json
```

Future queries similar to this one will be served directly from the cache, bypassing LLM and validation.

---

## Testing

### Unit tests (fast, no API key required)

```bash
uv run pytest tests/unit/ -v
```

Expected output:

```
tests/unit/test_validator.py::test_valid_position_report PASSED
tests/unit/test_validator.py::test_missing_required_field PASSED
tests/unit/test_state_machine.py::test_valid_sr_to_fs_sequence PASSED
tests/unit/test_cross_message.py::test_consistent_qscale PASSED
tests/unit/test_instantiator.py::test_t_train_instantiated PASSED
...
17 passed in X.XXs
```

### Integration tests (require `.env` with DB and API key)

```bash
uv run pytest tests/integration/ -m integration -v
```

### Single test

```bash
uv run pytest tests/unit/test_validator.py::test_missing_required_field -v
```

---

## Lint, format, type check

```bash
# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

---

## Project structure

```
agentic_pipeline/
├── src/etcs_pipeline/
│   ├── main.py                  # CLI entry point (Typer)
│   ├── config/
│   │   ├── settings.py          # GlobalConfig (Pydantic-Settings, loads .env)
│   │   ├── llm_client.py        # build_llm_client() — Anthropic/OpenAI factory
│   │   └── loader.py            # ProfileLoader — resolves paths from profile.yaml
│   ├── models/                  # Pydantic v2 data models
│   ├── components/
│   │   ├── normalizer.py        # [LLM] extracts features from NL query
│   │   ├── planner.py           # [LLM] generates the message LinkedList
│   │   ├── validator.py         # [deterministic] formal ETCS validation
│   │   ├── plausibility/        # [deterministic] state machine, cross-msg, kinematics
│   │   ├── instantiator.py      # [deterministic] fills default values from YAML
│   │   └── formatter.py         # [deterministic] formats the final output
│   ├── core/
│   │   ├── state.py             # PipelineState TypedDict
│   │   ├── graph.py             # build_graph() — LangGraph with conditional routing
│   │   └── runner.py            # PipelineRunner — orchestration
│   ├── rag/                     # PostgreSQL + pgvector + sentence-transformers
│   └── cache/                   # Semantic cache on pgvector
├── profiles/etcs/               # Domain spec, rules, prompts, example chains
│   ├── profile.yaml             # Path mapping (no operational values)
│   ├── spec/subset026_v360.md   # ETCS Subset-026 v3.6.0 specification
│   ├── rules/                   # messages.yaml, crossmessage.yaml
│   ├── prompts/                 # System prompts for normalizer and planner
│   └── chains/                  # 5 validated example chains
├── tests/
│   ├── unit/                    # 17 deterministic tests (no LLM/DB)
│   └── integration/             # End-to-end tests (require .env)
├── docs/                        # Architecture, business analysis, tech specs
├── .env.example                 # Configuration template
└── pyproject.toml
```

---

## Architecture — configuration layers

| Layer | File | Content |
|-------|------|---------|
| Operational | `.env` → `GlobalConfig` | API keys, DB credentials, thresholds, provider |
| Domain | `profiles/etcs/profile.yaml` → `ProfileLoader` | Paths to spec files only |
| Rules | `profiles/etcs/rules/messages.yaml` | Required/conditional fields per message |

> `profile.yaml` contains no operational values — it is a path index only.

---

## Troubleshooting

**`pgvector` not found**
```
HINT: No function matches the given name and argument types
```
Install the extension as superuser: `CREATE EXTENSION vector;`

**Slow embedding on first run**
The `paraphrase-multilingual-MiniLM-L12-v2` model is downloaded from HuggingFace on first use (~90 MB). Subsequent runs use the local cache.

**`etcs-pipeline` command not found**
Make sure you ran `uv sync` and always prefix with `uv run etcs-pipeline ...`
