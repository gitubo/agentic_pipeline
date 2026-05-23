from pathlib import Path


def load_spec_documents(spec_path: Path):
    from llama_index.core import SimpleDirectoryReader
    from llama_index.core.node_parser import MarkdownNodeParser

    reader = SimpleDirectoryReader(input_files=[spec_path])
    documents = reader.load_data()
    parser = MarkdownNodeParser()
    return parser.get_nodes_from_documents(documents)
