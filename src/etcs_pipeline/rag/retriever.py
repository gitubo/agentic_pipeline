from pathlib import Path
from etcs_pipeline.models.scenario import ScenarioFeatures
from etcs_pipeline.config.loader import ProfileLoader


class RagRetriever:
    def __init__(self, loader: ProfileLoader):
        from llama_index.core import VectorStoreIndex, StorageContext
        from llama_index.vector_stores.postgres import PGVectorStore
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        from llama_index.core import Settings
        import sqlalchemy

        config = loader.get_component_config("rag")
        db_config = loader.get_db_config()

        self._hints: dict = loader.load_rag_hints()

        embed_model = HuggingFaceEmbedding(model_name=config["embedding_model"])
        Settings.embed_model = embed_model
        Settings.chunk_size = config["chunk_size"]
        Settings.chunk_overlap = config["chunk_overlap"]

        vector_store = PGVectorStore.from_params(
            database=db_config["database"],
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            table_name=config["pg_table"],
            embed_dim=config["embedding_dim"],
        )

        connection_string = (
            f"postgresql+psycopg://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
        engine = sqlalchemy.create_engine(connection_string)
        with engine.connect() as conn:
            try:
                count = conn.execute(
                    sqlalchemy.text(f"SELECT COUNT(*) FROM {config['pg_table']}")
                ).scalar_one_or_none()
            except Exception:
                count = 0

        if not count:
            self._index = self._build_index(loader.get_spec_path(), vector_store)
        else:
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            self._index = VectorStoreIndex.from_vector_store(
                vector_store, storage_context=storage_context
            )

        self._retriever = self._index.as_retriever(similarity_top_k=config["top_k"])

    def retrieve(self, features: ScenarioFeatures) -> str:
        query_terms = self._features_to_query(features)
        nodes = self._retriever.retrieve(query_terms)
        return "\n\n---\n\n".join(n.get_content() for n in nodes)

    def _features_to_query(self, features: ScenarioFeatures) -> str:
        terms = [f"mode {features.initial_mode}"]
        terms.extend(self._hints.get("static", []))
        conditional = self._hints.get("conditional", {})
        if features.gradient_profile:
            terms.extend(conditional.get("gradient_profile", []))
        if len(features.sections) > 1:
            terms.extend(conditional.get("multi_section", []))
        return " ".join(terms)

    @staticmethod
    def _build_index(spec_path: Path, vector_store):
        from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
        from llama_index.core.node_parser import MarkdownNodeParser

        reader = SimpleDirectoryReader(input_files=[spec_path])
        documents = reader.load_data()
        parser = MarkdownNodeParser()
        nodes = parser.get_nodes_from_documents(documents)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        return VectorStoreIndex(nodes, storage_context=storage_context, show_progress=True)
