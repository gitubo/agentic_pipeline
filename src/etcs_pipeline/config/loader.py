from pathlib import Path
import yaml
from etcs_pipeline.config.settings import get_config, GlobalConfig


class ProfileLoader:
    """
    Resolves paths for the domain profile.
    Operational values (max_rerun, top_k, etc.) come from GlobalConfig,
    not from this loader — never duplicated.
    """

    def __init__(
        self,
        profile_name: str | None = None,
        settings: GlobalConfig | None = None,
    ):
        self._settings = settings or get_config()
        name = profile_name or self._settings.active_profile
        profiles_root = Path(self._settings.profiles_root)
        self.profile_root = profiles_root / name
        self._profile = self._load_yaml(self.profile_root / "profile.yaml")

    # ── Path resolution ────────────────────────────────────────────────────

    def get_spec_path(self) -> Path:
        return self._resolve(self._profile["paths"]["spec"])

    def get_chains_path(self) -> Path:
        return self._resolve(self._profile["paths"]["chains"])

    def get_pg_table(self, store: str) -> str:
        return self._profile["paths"]["pg_tables"][store]

    def load_rules(self) -> dict:
        return self._load_yaml(
            self._resolve(self._profile["paths"]["rules"]["messages"])
        )

    def load_crossmessage_rules(self) -> dict:
        return self._load_yaml(
            self._resolve(self._profile["paths"]["rules"]["crossmessage"])
        )

    def load_state_machine(self) -> dict:
        return self._load_yaml(
            self._resolve(self._profile["paths"]["statemachine"])
        )

    def load_kinematics(self) -> dict:
        return self._load_yaml(
            self._resolve(self._profile["paths"]["kinematics"])
        )

    def load_defaults(self) -> dict:
        return self._load_yaml(
            self._resolve(self._profile["paths"]["instantiator_defaults"])
        )

    def get_instantiator_field_names(self) -> set[str]:
        """Return all field names defined in the instantiator defaults."""
        defaults = self.load_defaults()
        fields: set[str] = set(defaults.get("session", {}).keys())
        for msg_def in defaults.get("per_message", []):
            fields.update(msg_def.get("fields", {}).keys())
        for pkt_def in defaults.get("per_packet", []):
            fields.update(pkt_def.get("fields", {}).keys())
        return fields

    def load_rag_hints(self) -> dict:
        return self._load_yaml(
            self._resolve(self._profile["paths"]["rag_hints"])
        )

    def load_prompt(self, name: str) -> str:
        path = self._resolve(self._profile["paths"]["prompts"][name])
        return path.read_text(encoding="utf-8")

    def load_schema(self, name: str) -> dict:
        import json
        path = self._resolve(self._profile["paths"]["schemas"][name])
        return json.loads(path.read_text(encoding="utf-8"))

    def get_spec_version(self) -> str:
        return self._profile["spec_version"]

    def get_db_config(self) -> dict:
        """Return DB parameters from GlobalConfig (not from profile)."""
        cfg = self._settings
        return {
            "host": cfg.db_host,
            "port": cfg.db_port,
            "database": cfg.db_name,
            "user": cfg.db_user,
            "password": cfg.db_password,
            "schema": cfg.db_schema,
        }

    def get_component_config(self, component: str) -> dict:
        """
        Build the operational configuration for a component
        by combining GlobalConfig (values) and profile.yaml (paths).
        """
        cfg = self._settings
        if component == "rag":
            return {
                "embedding_model": cfg.embedding_model,
                "embedding_dim": cfg.embedding_dim,
                "chunk_size": cfg.rag_chunk_size,
                "chunk_overlap": cfg.rag_chunk_overlap,
                "top_k": cfg.rag_top_k,
                "pg_table": self.get_pg_table("rag"),
            }
        if component == "cache":
            return {
                "embedding_model": cfg.embedding_model,
                "embedding_dim": cfg.embedding_dim,
                "top_k": cfg.cache_top_k,
                "similarity_threshold": cfg.cache_similarity_threshold,
                "pg_table": self.get_pg_table("cache"),
            }
        raise ValueError(f"Unsupported component: {component}")

    # ── Internals ──────────────────────────────────────────────────────────

    def _resolve(self, relative: str) -> Path:
        return (self.profile_root / relative).resolve()

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
