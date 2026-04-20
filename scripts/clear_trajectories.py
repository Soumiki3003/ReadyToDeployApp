"""Clear all UserTrajectory nodes from Neo4j."""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASS", "password")),
)

with driver.session() as session:
    result = session.run("MATCH (t:UserTrajectory) DETACH DELETE t RETURN count(t) AS deleted")
    print(f"Deleted {result.single()['deleted']} trajectory nodes.")

driver.close()
