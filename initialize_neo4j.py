"""Creates constraints and loads the sample data into Neo4j. Usage: python -m scripts.initialize_neo4j"""
import pathlib
from src import graph as g, neo4j_service as ns
ok, msg = ns.test_connection(); print(msg)
if ok:
    df, _ = g.load_docs(pathlib.Path(__file__).resolve().parents[1] / "data" / "sample_documents.csv")
    print("Loaded documents/references:", ns.load_documents(df))
