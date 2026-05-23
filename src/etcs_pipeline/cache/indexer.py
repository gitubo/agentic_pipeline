import json
from pathlib import Path
from etcs_pipeline.cache.semantic_cache import SemanticCache


def index_chains_from_directory(chains_dir: Path, cache: SemanticCache) -> int:
    """
    Reads all .json files in chains_dir and adds them to the SemanticCache.
    Returns the number of chains indexed.
    """
    count = 0
    for f in sorted(chains_dir.glob("*.json")):
        chain = json.loads(f.read_text(encoding="utf-8"))
        cache.add_chain(chain)
        count += 1
    return count
