"""Loading, graph building and analysis.
Graph = undirected projection of the full heterogeneous graph (Document, Department,
Project, Topic, Role). All centralities and communities are computed on this graph."""
import pandas as pd, networkx as nx
from networkx.algorithms import community as nxc

REQ = ["document_id", "title", "department", "project", "date", "document_type", "topics", "references", "owner_role"]
split = lambda v: [x.strip() for x in str(v).split(";") if x.strip()]

def load_docs(src):
    """Returns (clean DataFrame, list of issue messages). Raises ValueError on missing columns."""
    df = src.copy() if isinstance(src, pd.DataFrame) else pd.read_csv(src, dtype=str)
    miss = [c for c in REQ if c not in df.columns]
    if miss:
        raise ValueError(f"Missing required columns: {miss}")
    df = df[REQ].fillna("").astype(str).apply(lambda s: s.str.strip())
    issues = []
    bad = (df.document_id == "") | (df.title == "")
    if bad.any():
        issues.append(f"{int(bad.sum())} row(s) without ID/title were dropped.")
    df = df[~bad]
    dup = df.document_id.duplicated()
    if dup.any():
        issues.append(f"Duplicate IDs dropped (first kept): {sorted(df[dup].document_id.unique())}")
    return df[~dup].reset_index(drop=True), issues

def build_graph(df):
    """Returns (graph, unresolved_refs). Edges come only from metadata; references need an existing target."""
    G, unresolved, ids = nx.Graph(), [], set(df.document_id)
    def node(kind, key, label=None):
        n = f"{kind}:{key}"; G.add_node(n, type=kind, label=label or key); return n
    def edge(a, b, rel): G.add_edge(a, b, rel=rel)
    for r in df.itertuples():
        d = node("Document", r.document_id, r.document_id)
        G.nodes[d].update(title=r.title, date=r.date, doc_type=r.document_type)
        for kind, val, rel in [("Department", r.department, "BELONGS_TO"), ("Project", r.project, "RELATES_TO"),
                               ("Role", r.owner_role, "OWNED_BY")]:
            if val: edge(d, node(kind, val), rel)
        for t in split(r.topics): edge(d, node("Topic", t), "DISCUSSES")
        for ref in split(r.references):
            if ref in ids and ref != r.document_id: edge(d, f"Document:{ref}", "REFERENCES")
            else: unresolved.append((r.document_id, ref))
    return G, unresolved

def centrality(G):
    if G.number_of_nodes() == 0: return pd.DataFrame()
    m = {"degree": nx.degree_centrality(G), "betweenness": nx.betweenness_centrality(G),
         "closeness": nx.closeness_centrality(G), "pagerank": nx.pagerank(G) if G.number_of_edges() else {n: 1 / len(G) for n in G}}
    rows = [{"node": n, "label": G.nodes[n]["label"], "type": G.nodes[n]["type"], **{k: v[n] for k, v in m.items()}} for n in G]
    return pd.DataFrame(rows)

def communities(G):
    """Greedy modularity (deterministic). Returns {node: community_id}, largest community first."""
    if G.number_of_nodes() == 0: return {}
    comms = nxc.greedy_modularity_communities(G) if G.number_of_edges() else [{n} for n in G]
    return {n: i for i, c in enumerate(sorted(comms, key=len, reverse=True)) for n in c}

def community_summary(G, comm):
    rows = []
    for cid in sorted(set(comm.values())):
        ns = [n for n, c in comm.items() if c == cid]
        top = lambda k: ", ".join(sorted(G.nodes[n]["label"] for n in ns if G.nodes[n]["type"] == k))
        rows.append({"community": cid, "nodes": len(ns), "documents": sum(G.nodes[n]["type"] == "Document" for n in ns),
                     "topics": top("Topic"), "departments": top("Department"), "projects": top("Project")})
    return pd.DataFrame(rows)

def related_documents(G, doc_id):
    """Other documents ranked by WHY they connect: shared topics/department/project/role or direct reference."""
    me, rows = f"Document:{doc_id}", []
    if me not in G: return pd.DataFrame()
    shared = lambda n: {x for x in G[n] if G.nodes[x]["type"] != "Document"}
    mine = shared(me)
    for n in G:
        if G.nodes[n]["type"] != "Document" or n == me: continue
        common = mine & shared(n); ref = G.has_edge(me, n)
        if common or ref:
            rows.append({"document": G.nodes[n]["label"], "title": G.nodes[n]["title"], "direct_reference": ref,
                         "shared": ", ".join(sorted(G.nodes[x]["label"] for x in common)), "score": len(common) + 2 * ref})
    return pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()

def neighborhood(G, n, hops=1): return nx.ego_graph(G, n, radius=hops)

def relationships_df(G):
    return pd.DataFrame([{"source": G.nodes[a]["label"], "source_type": G.nodes[a]["type"], "relationship": d["rel"],
                          "target": G.nodes[b]["label"], "target_type": G.nodes[b]["type"], "basis": "metadata"}
                         for a, b, d in G.edges(data=True)])
