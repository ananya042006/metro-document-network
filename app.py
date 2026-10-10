import pathlib, pandas as pd, plotly.express as px, streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network
from src import graph as g, neo4j_service as ns

st.set_page_config(page_title="Metro Document Network", layout="wide")
st.markdown("""<style>.block-container{padding-top:2rem}
[data-testid=stMetric]{background:#111a2e;border:1px solid #1e2d4a;border-left:3px solid #2dd4bf;padding:12px 16px;border-radius:4px}
[data-testid=stSidebar]{border-right:1px solid #1e2d4a}</style>""", unsafe_allow_html=True)
COL = {"Document": "#22d3ee", "Department": "#f59e0b", "Project": "#a78bfa", "Topic": "#34d399", "Role": "#f472b6"}
SAMPLE = pathlib.Path(__file__).parent / "data" / "sample_documents.csv"
PAL = ["#22d3ee", "#f59e0b", "#a78bfa", "#34d399", "#f472b6", "#f87171", "#60a5fa", "#fbbf24"]
RELS = ["BELONGS_TO", "RELATES_TO", "OWNED_BY", "DISCUSSES", "REFERENCES"]

if "df" not in st.session_state:
    st.session_state.df, st.session_state.source = g.load_docs(SAMPLE)[0], "Demo data (synthetic sample CSV)"
df = st.session_state.df

@st.cache_data
def analyse(df):
    G, unresolved = g.build_graph(df)
    return G, unresolved, g.centrality(G), g.communities(G)
G, unresolved, cen, comm = analyse(df)

st.sidebar.title("Metro Document Network")
page = st.sidebar.radio("Navigate", ["Overview", "Document Explorer", "Relationship Graph", "Centrality", "Communities", "Data & Neo4j"])
st.sidebar.caption(f"Data source: {st.session_state.source}")

def draw(H, color_of, height=620):
    net = Network(height=f"{height}px", width="100%", bgcolor="#0b1220", font_color="#e2e8f0", cdn_resources="in_line")
    for n, d in H.nodes(data=True):
        net.add_node(n, label=d["label"], color=color_of(n), size=8 + 3 * H.degree(n),
                     title=f"{d['type']}: {d.get('title', d['label'])}", shape="dot" if d["type"] == "Document" else "diamond")
    for a, b, d in H.edges(data=True): net.add_edge(a, b, title=d["rel"], color="#334155")
    components.html(net.generate_html(), height=height + 20)

deg = pd.Series({n: G.degree(n) for n in G}, name="deg")
if df.empty:
    st.warning("No documents loaded. Use Data & Neo4j to reset to the sample data.")
if page == "Overview" and not df.empty:
    st.header("Overview")
    types = pd.Series({n: d["type"] for n, d in G.nodes(data=True)})
    for col, (k, v) in zip(st.columns(6), [("Documents", (types == "Document").sum()), ("Departments", (types == "Department").sum()),
                              ("Projects", (types == "Project").sum()), ("Topics", (types == "Topic").sum()),
                              ("Roles", (types == "Role").sum()), ("Relationships", G.number_of_edges())]): col.metric(k, int(v))
    docs = cen[cen.type == "Document"].merge(deg, left_on="node", right_index=True).sort_values("deg")
    tops = cen[cen.type == "Topic"].merge(deg, left_on="node", right_index=True).sort_values("deg")
    a, b = st.columns(2)
    a.info(f"Most connected document: **{docs.iloc[-1].label}** ({G.nodes[docs.iloc[-1].node]['title']})")
    if not tops.empty: b.info(f"Most connected topic: **{tops.iloc[-1].label}** ({int(tops.deg.iloc[-1])} documents)")
    a, b = st.columns(2)
    a.plotly_chart(px.bar(df.department.value_counts().reset_index(), x="count", y="department", orientation="h", title="Documents by department", color_discrete_sequence=["#2dd4bf"]), use_container_width=True)
    t = df.assign(month=pd.to_datetime(df.date, errors="coerce").dt.to_period("M").astype(str)).groupby(["month", "document_type"]).size().reset_index(name="n")
    b.plotly_chart(px.bar(t, x="month", y="n", color="document_type", title="Documents by month and type"), use_container_width=True)
    st.subheader("Network summary"); draw(G, lambda n: COL[G.nodes[n]["type"]], 480)
    st.subheader("Most recent documents"); st.dataframe(df.sort_values("date", ascending=False).head(5)[["document_id", "title", "department", "date"]], hide_index=True)

elif page == "Document Explorer" and not df.empty:
    st.header("Document Explorer")
    q = st.text_input("Search by title or ID")
    f1, f2, f3, f4 = st.columns(4)
    dep = f1.multiselect("Department", sorted(df.department.unique())); prj = f2.multiselect("Project", sorted(df.project.unique()))
    typ = f3.multiselect("Type", sorted(df.document_type.unique()))
    top = f4.multiselect("Topic", sorted({t for v in df.topics for t in g.split(v)}))
    v = df
    if q: v = v[v.title.str.contains(q, case=False, regex=False) | v.document_id.str.contains(q, case=False, regex=False)]
    if dep: v = v[v.department.isin(dep)]
    if prj: v = v[v.project.isin(prj)]
    if typ: v = v[v.document_type.isin(typ)]
    if top: v = v[v.topics.apply(lambda s: bool(set(g.split(s)) & set(top)))]
    st.dataframe(v[["document_id", "title", "department", "project", "date", "document_type", "topics"]], hide_index=True, use_container_width=True)
    if v.empty: st.info("No documents match these filters.")
    else:
        sel = st.selectbox("Inspect document", v.document_id); n = f"Document:{sel}"
        st.subheader(f"{sel}: {G.nodes[n]['title']}")
        nb = pd.DataFrame([{"type": G.nodes[x]["type"], "node": G.nodes[x]["label"], "relationship": G[n][x]["rel"]} for x in G[n]])
        st.dataframe(nb.sort_values(["type", "node"]), hide_index=True)
        st.markdown("**Why are other documents connected?** Shared items come from metadata; score is shared-item count (+2 for a direct reference).")
        rel = g.related_documents(G, sel)
        if rel.empty: st.info("No related documents.")
        else: st.dataframe(rel, hide_index=True)

elif page == "Relationship Graph" and not df.empty:
    st.header("Relationship Graph")
    a, b, c = st.columns(3)
    kinds = a.multiselect("Node types", list(COL), default=list(COL))
    rels = b.multiselect("Relationship types", RELS, default=RELS)
    focus = c.selectbox("Focus node (optional)", ["(whole graph)"] + sorted(G.nodes))
    hops = st.slider("Neighbourhood hops", 1, 2, 1) if focus != "(whole graph)" else 1
    H = G if focus == "(whole graph)" else g.neighborhood(G, focus, hops)
    H = H.edge_subgraph([(u, v) for u, v, d in H.edges(data=True) if d["rel"] in rels]).copy()
    H.remove_nodes_from([n for n in list(H) if H.nodes[n]["type"] not in kinds])
    if H.number_of_nodes() == 0: st.info("Nothing to show with these filters.")
    else:
        st.markdown(" ".join(f"<span style='color:{c}'>■</span> {k}" for k, c in COL.items()) + " &nbsp; Documents are circles, other nodes diamonds. Hover for details.", unsafe_allow_html=True)
        draw(H, lambda n: COL[G.nodes[n]["type"]])
        if focus != "(whole graph)": st.write("Direct neighbours:", ", ".join(G.nodes[x]["label"] for x in G[focus]))

elif page == "Centrality" and not df.empty:
    st.header("Centrality")
    st.caption("Computed on the full graph (all node types, undirected). High centrality shows structural position only, not quality or correctness.")
    m = st.radio("Metric", ["degree", "betweenness", "pagerank", "closeness"], horizontal=True)
    st.markdown({"degree": "Degree: how many direct connections a node has.", "betweenness": "Betweenness: how often a node lies on shortest paths between others, so it may bridge separate parts.",
                 "pagerank": "PageRank: importance based on being connected to other important nodes.", "closeness": "Closeness: how near a node is to all others."}[m])
    ty = st.multiselect("Node types", list(COL), default=["Document", "Topic"])
    top = cen[cen.type.isin(ty)].sort_values(m, ascending=False).head(15)
    st.plotly_chart(px.bar(top, x=m, y="label", color="type", orientation="h", color_discrete_map=COL).update_yaxes(autorange="reversed"), use_container_width=True)
    st.dataframe(top.drop(columns="node").round(4), hide_index=True, use_container_width=True)

elif page == "Communities" and not df.empty:
    st.header("Communities")
    st.caption("Greedy modularity on the full graph. Communities reflect network structure, not verified organisational categories.")
    st.dataframe(g.community_summary(G, comm), hide_index=True, use_container_width=True)
    draw(G, lambda n: PAL[comm[n] % len(PAL)])

elif page == "Data & Neo4j":
    st.header("Data & Neo4j")
    st.subheader("Data management")
    if unresolved: st.warning(f"Unresolved references (ignored): {unresolved}")
    st.download_button("Export documents CSV", df.to_csv(index=False), "documents.csv")
    st.download_button("Export relationships CSV", g.relationships_df(G).to_csv(index=False), "relationships.csv")
    up = st.file_uploader("Import CSV (columns: " + ", ".join(g.REQ) + ")", type="csv")
    if up:
        try:
            new, issues = g.load_docs(up); st.dataframe(new.head(), hide_index=True)
            for i in issues: st.warning(i)
            if st.button("Replace current data with this CSV"):
                st.session_state.df, st.session_state.source = new, f"Uploaded CSV ({up.name}), local only"; st.rerun()
        except ValueError as e: st.error(str(e))
    if st.checkbox("I understand this discards imported data") and st.button("Reset to sample data"):
        st.session_state.df, st.session_state.source = g.load_docs(SAMPLE)[0], "Demo data (synthetic sample CSV)"; st.rerun()
    st.subheader("Neo4j (optional)")
    st.caption("Set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in your environment. Analysis pages always use the local copy above.")
    if st.button("Test connection"):
        ok, msg = ns.test_connection(); (st.success if ok else st.error)(msg)
    if st.button("Load current data into Neo4j"):
        try: n, r = ns.load_documents(df); st.success(f"Wrote {n} documents and {r} references to Neo4j.")
        except Exception as e: st.error(f"Load failed ({type(e).__name__}). Is Neo4j running and configured?")
    q = st.selectbox("Predefined read-only query", list(ns.QUERIES)); st.caption(ns.QUERIES[q][0]); st.code(ns.QUERIES[q][1], "cypher")
    if st.button("Run query"):
        try:
            res = ns.run_query(q)
            if res: st.dataframe(pd.DataFrame(res), hide_index=True)
            else: st.info("Query returned no rows.")
        except Exception as e: st.error(f"Query failed ({type(e).__name__}). Is Neo4j running and loaded?")
