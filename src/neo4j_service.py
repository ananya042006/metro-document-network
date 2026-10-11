"""Optional Neo4j integration. Credentials come from environment variables only."""
import os
from neo4j import GraphDatabase
from .graph import split

CONSTRAINTS = ["CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (n:Document) REQUIRE n.id IS UNIQUE"] + [
    f"CREATE CONSTRAINT {k.lower()}_name IF NOT EXISTS FOR (n:{k}) REQUIRE n.name IS UNIQUE"
    for k in ("Department", "Project", "Topic", "Role")]
LOAD = """UNWIND $rows AS r
MERGE (d:Document {id:r.id}) SET d.title=r.title, d.type=r.type, d.date=r.date
MERGE (dep:Department {name:r.dept}) MERGE (d)-[:BELONGS_TO]->(dep)
MERGE (p:Project {name:r.project}) MERGE (d)-[:RELATES_TO]->(p)
MERGE (o:Role {name:r.role}) MERGE (d)-[:OWNED_BY]->(o)
WITH d, r UNWIND r.topics AS t MERGE (tp:Topic {name:t}) MERGE (d)-[:DISCUSSES]->(tp)"""
REFS = """UNWIND $refs AS x MATCH (a:Document {id:x.src}), (b:Document {id:x.dst}) MERGE (a)-[:REFERENCES]->(b)"""
# Predefined, read-only queries (no free-form Cypher is executed).
QUERIES = {
    "Most-referenced documents": ("Documents ranked by incoming REFERENCES.",
        "MATCH (d:Document)<-[r:REFERENCES]-() RETURN d.id AS id, d.title AS title, count(r) AS citations ORDER BY citations DESC LIMIT 10"),
    "Cross-department dependencies": ("Department pairs linked by document references.",
        "MATCH (a:Department)<-[:BELONGS_TO]-(:Document)-[:REFERENCES]->(:Document)-[:BELONGS_TO]->(b:Department) WHERE a<>b RETURN a.name AS from_dept, b.name AS to_dept, count(*) AS links ORDER BY links DESC"),
    "Orphan documents": ("Documents with no reference links in either direction.",
        "MATCH (d:Document) WHERE NOT (d)-[:REFERENCES]-(:Document) RETURN d.id AS id, d.title AS title"),
    "Busiest topics": ("Topics ranked by number of documents discussing them.",
        "MATCH (t:Topic)<-[:DISCUSSES]-(d) RETURN t.name AS topic, count(d) AS documents ORDER BY documents DESC"),
    "Shared-topic document pairs": ("Pairs of documents sharing 2+ topics.",
        "MATCH (a:Document)-[:DISCUSSES]->(t)<-[:DISCUSSES]-(b:Document) WHERE a.id<b.id WITH a,b,collect(t.name) AS topics WHERE size(topics)>=2 RETURN a.id AS doc_a, b.id AS doc_b, topics"),
}
def _driver():
    return GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                                auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")))
def test_connection():
    try:
        with _driver() as d: d.verify_connectivity()
        return True, "Connected to Neo4j."
    except Exception as e:
        return False, f"Neo4j unavailable ({type(e).__name__}). Check NEO4J_URI/USER/PASSWORD and that the server is running."
def load_documents(df):
    rows = [dict(id=r.document_id, title=r.title, type=r.document_type, date=r.date, dept=r.department,
                 project=r.project, role=r.owner_role, topics=split(r.topics)) for r in df.itertuples()]
    ids = set(df.document_id)
    refs = [dict(src=r.document_id, dst=x) for r in df.itertuples() for x in split(r.references) if x in ids and x != r.document_id]
    with _driver() as d, d.session() as s:
        for c in CONSTRAINTS: s.run(c)
        s.execute_write(lambda tx: (tx.run(LOAD, rows=rows), tx.run(REFS, refs=refs)))
    return len(rows), len(refs)
def run_query(name):
    with _driver() as d, d.session() as s:
        return [r.data() for r in s.run(QUERIES[name][1])]
