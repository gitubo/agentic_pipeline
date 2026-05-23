import json
from pathlib import Path
import numpy as np
from etcs_pipeline.models.scenario import ScenarioFeatures
from etcs_pipeline.config.loader import ProfileLoader


class SemanticCache:
    """
    Libreria di catene validate con pgvector.
    Embedding locale con sentence-transformers — zero dipendenze API esterne.
    """

    _model = None

    def __init__(self, loader: ProfileLoader):
        config = loader.get_component_config("cache")
        db = loader.get_db_config()

        self._top_k = config["top_k"]
        self._threshold = config["similarity_threshold"]
        self._table = config["pg_table"]
        self._model_name = config["embedding_model"]
        self._dim = config["embedding_dim"]

        self._conn_str = (
            f"host={db['host']} port={db['port']} "
            f"dbname={db['database']} user={db['user']} "
            f"password={db['password']}"
        )

        self._ensure_table()

        with self._connect() as conn:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {self._table}"
            ).fetchone()[0]

        if count == 0:
            self._index_chains(loader.get_chains_path())

    def retrieve(
        self, features: ScenarioFeatures
    ) -> tuple[list[str], list[dict]]:
        query_text = self._features_to_text(features)
        embedding = self._embed(query_text)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT chain_id, chain_json,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM {self._table}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding.tolist(), embedding.tolist(), self._top_k),
            ).fetchall()

        hits, chains = [], []
        for chain_id, chain_json, similarity in rows:
            if similarity >= self._threshold:
                hits.append(chain_id)
                chains.append(json.loads(chain_json))

        return hits, chains

    def add_chain(self, chain: dict) -> None:
        chain_id = chain["id"]
        text = self._chain_to_text(chain)
        embedding = self._embed(text)

        with self._connect() as conn:
            conn.execute(
                f"""
                INSERT INTO {self._table} (chain_id, chain_json, embedding)
                VALUES (%s, %s, %s::vector)
                ON CONFLICT (chain_id) DO UPDATE
                    SET chain_json = EXCLUDED.chain_json,
                        embedding  = EXCLUDED.embedding
                """,
                (chain_id, json.dumps(chain), embedding.tolist()),
            )

    # ── Internals ──────────────────────────────────────────────────────────

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    chain_id   TEXT PRIMARY KEY,
                    chain_json JSONB NOT NULL,
                    embedding  vector({self._dim}) NOT NULL
                )
            """)
            conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {self._table}_embedding_idx
                ON {self._table}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)

    def _connect(self):
        import psycopg
        from pgvector.psycopg import register_vector
        conn = psycopg.connect(self._conn_str, autocommit=True)
        register_vector(conn)
        return conn

    def _embed(self, text: str) -> np.ndarray:
        return self._get_model().encode(text, normalize_embeddings=True)

    def _get_model(self):
        from sentence_transformers import SentenceTransformer
        if SemanticCache._model is None:
            SemanticCache._model = SentenceTransformer(self._model_name)
        return SemanticCache._model

    def _index_chains(self, chains_path: Path) -> None:
        for f in sorted(chains_path.glob("*.json")):
            chain = json.loads(f.read_text(encoding="utf-8"))
            self.add_chain(chain)

    @staticmethod
    def _features_to_text(features: ScenarioFeatures) -> str:
        parts = [
            f"mode:{features.initial_mode}",
            f"sections:{len(features.sections)}",
            f"eoa:{features.eoa_distance_m}m",
        ]
        if features.gradient_profile:
            parts.append("gradient:yes")
        speeds = sorted({s.v_max_kmh for s in features.sections})
        parts.append(f"speeds:{speeds}")
        return " ".join(parts)

    @staticmethod
    def _chain_to_text(chain: dict) -> str:
        msg_names = [
            m.get("name", str(m.get("nid_message")))
            for m in chain.get("chain", [])
        ]
        return " ".join([
            chain.get("description", ""),
            *msg_names,
            str(chain.get("features", {})),
        ])
