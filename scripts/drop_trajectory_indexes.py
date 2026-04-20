"""
One-time migration: drop old trajectory indexes so they get recreated
with the correct node label (UserTrajectory) and field (trajectory_vector).
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASS", "password")

driver = GraphDatabase.driver(uri, auth=(user, password))

indexes_to_drop = [
    "index_trajectory_query_vector",
    "index_trajectory_query_text",
]

with driver.session() as session:
    for name in indexes_to_drop:
        session.run(f"DROP INDEX {name} IF EXISTS")
        print(f"Dropped index: {name}")

driver.close()
print("Done. Restart Flask to recreate indexes with correct config.")
