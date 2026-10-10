import pandas as pd, pytest
from src import graph as g, neo4j_service as ns
from scripts.seed_data import build
DF = lambda: g.load_docs(pd.DataFrame(build()))[0]
def test_sample_loads_and_graph():
    G, un = g.build_graph(DF()); assert len(DF()) == 32 and G.number_of_edges() > 100 and un == []
def test_missing_columns():
    with pytest.raises(ValueError): g.load_docs(pd.DataFrame({"title": ["x"]}))
def test_duplicates_and_unresolved():
    d = pd.DataFrame(build()[:2]); d.loc[1, "document_id"] = d.loc[0, "document_id"]
    df, issues = g.load_docs(d); assert len(df) == 1 and issues
    df.loc[0, "references"] = "DOC-999;DOC-001"; _, un = g.build_graph(df); assert len(un) == 2
def test_centrality_and_communities():
    G, _ = g.build_graph(DF()); c = g.centrality(G); assert c.pagerank.sum() == pytest.approx(1)
    assert len(set(g.communities(G).values())) >= 2
def test_empty():
    G, _ = g.build_graph(g.load_docs(pd.DataFrame(columns=g.REQ))[0]); assert g.centrality(G).empty and g.communities(G) == {}
def test_neo4j_failure(monkeypatch):
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:1"); ok, msg = ns.test_connection(); assert not ok and "unavailable" in msg
def test_export_has_columns():
    G, _ = g.build_graph(DF()); assert {"source", "relationship", "target"} <= set(g.relationships_df(G).columns)
