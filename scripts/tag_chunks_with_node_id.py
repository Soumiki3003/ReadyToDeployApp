"""
Migration: tag each ContentChunk with the KG node it came from.
Matches chunk content prefix against node labels (descriptive names).
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASS", "password")),
)

with driver.session() as session:
    result = session.run("""
        MATCH (c:ContentChunk), (n)
        WHERE n.label IS NOT NULL AND n.name IS NOT NULL
          AND c.content STARTS WITH n.label
        SET c.kg_node_id = n.name
        RETURN count(c) AS tagged
    """)
    tagged = result.single()["tagged"]
    print(f"Tagged {tagged} chunks with kg_node_id")

    # Report coverage
    total = session.run("MATCH (c:ContentChunk) RETURN count(c) AS n").single()["n"]
    untagged = session.run("MATCH (c:ContentChunk) WHERE c.kg_node_id IS NULL RETURN count(c) AS n").single()["n"]
    print(f"Total: {total}, tagged: {total - untagged}, untagged: {untagged}")

    # Sample
    sample = session.run("""
        MATCH (c:ContentChunk) WHERE c.kg_node_id IS NOT NULL
        RETURN c.kg_node_id AS nid, left(c.content, 60) AS content
        LIMIT 10
    """)
    print("\nSample tagged chunks:")
    for r in sample:
        print(f"  {r['nid']} | {r['content']}")

driver.close()
