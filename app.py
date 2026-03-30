from flask import Flask, render_template, request, jsonify, redirect, url_for
import json, os
from parsers.dual_parser import parse_dualpath
from neo4j import GraphDatabase
import re

# === Flask setup ===
app = Flask(__name__)
UPLOAD_DIR = "static/uploads"
DATA_DIR = "data"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# === Neo4j setup ===
NEO4J_URI = "neo4j+s://1d0cca9a.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASS = "VVwrlfIgFASoThf5qb-vD-2r62HnNLuXthVzw8xnPPM"
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

# === ROUTE: Login Page ===

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # For now, ignore username/password and go straight to dashboard
        return redirect(url_for("dashboard"))
    return render_template("login.html")


# === ROUTE: File Upload + Dual Parser ===
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        uploaded_files = request.files.getlist("files")
        html_link = request.form.get("html_link", "")
        uploaded_paths = []

        for f in uploaded_files:
            if f and f.filename:
                path = os.path.join(UPLOAD_DIR, f.filename)
                f.save(path)
                uploaded_paths.append(path)
                print(f"📄 Uploaded: {path}")

                # Run dual-path parser
                generated = parse_dualpath(path)
                print(f"Generated KG JSON: {generated}")

        return jsonify({
            "uploaded": uploaded_paths,
            "html_link": html_link,
            "graph_generated": True
        })

    # GET request → just render upload form
    return render_template("upload.html")


# === ROUTE: Instructor Dashboard ===
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# === ROUTE: Student Progress Data ===
@app.route("/student-progress-data")
def student_progress_data():
    path = os.path.join("data", "student_state.json")
    if not os.path.exists(path):
        return jsonify({"students": []})
    with open(path, "r") as f:
        state = json.load(f)
    return jsonify(state)


# === ROUTE: Graph Visualization Page ===
@app.route("/graph")
def graph():
    return render_template("graph.html")


# === ROUTE: Graph Data (Now From Neo4j) ===
@app.route("/graph-data")
def graph_data():
    query = """
    MATCH (n)-[r]->(m)
    RETURN n, r, m
    """
    nodes, links = {}, []

    with driver.session() as session:
        results = session.run(query)
        for record in results:
            n = record["n"]
            r = record["r"]
            m = record["m"]

            if n["id"] not in nodes:
                nodes[n["id"]] = {
                    "id": n["id"],
                    "name": n.get("name", ""),
                    "label": list(n.labels)[0],
                    **{k: v for k, v in dict(n).items() if k not in ["id", "name"]}
                }
            if m["id"] not in nodes:
                nodes[m["id"]] = {
                    "id": m["id"],
                    "name": m.get("name", ""),
                    "label": list(m.labels)[0],
                    **{k: v for k, v in dict(m).items() if k not in ["id", "name"]}
                }

            links.append({
                "source": n["id"],
                "target": m["id"],
                "type": r.type if hasattr(r, "type") else "HAS_CHILD"
            })

    return jsonify({"nodes": list(nodes.values()), "links": links})


# === ROUTE: Root-level Conceptual Nodes (for initial render) ===
@app.route("/graph-root")
def graph_root():
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Concept)
            WHERE NOT (()-[:HAS_CHILD]->(c))
            RETURN c
        """)
        concept_nodes = [dict(r["c"]) for r in result]

    root = {"id": "root", "name": "Central node", "children": concept_nodes}
    return jsonify(root)


# === ROUTE: Expand Node on Demand ===
@app.route("/expand-node/<node_id>")
def expand_node(node_id):
    with driver.session() as session:
        results = session.run("""
            MATCH (n {id:$node_id})-[:HAS_CHILD|PROCEDURAL_FOR|ASSESSES]->(child)
            RETURN child
        """, node_id=node_id)
        children = [dict(r["child"]) for r in results]
    return jsonify(children)


# === Run Server ===
if __name__ == "__main__":
    app.run(debug=True)
