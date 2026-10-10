# Metro Document and Information Relationship Network Analysis (SIH25080)
All sample data is **synthetic** and not from Kochi Metro Rail Limited.

## Run (macOS / VS Code terminal)
    cd metro-document-network
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python -m scripts.seed_data      # regenerates data/sample_documents.csv
    python -m pytest -q
    streamlit run app.py             # http://localhost:8501

## Neo4j mode (optional)
    docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/yourpassword neo4j:5
    export NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=yourpassword
    python -m scripts.initialize_neo4j   # or use "Data & Neo4j" in the app
Analysis pages always use the local copy; Neo4j is used for loading and the predefined read-only queries.
