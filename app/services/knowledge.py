from contextlib import AbstractContextManager
import json
import logging
from pathlib import Path
from typing import Callable
from jinja2 import Template
from neo4j import Session, ManagedTransaction, unit_of_work
from neo4j_graphrag.indexes import upsert_vectors
from neo4j_graphrag.generation import GraphRAG
import pydantic_ai
from app import services, models


logger = logging.getLogger(__name__)


class KnowledgeService:
    __vector_property_name = "vector"
    __child_relation_type = "HAS_CHILD"

    def __init__(
        self,
        *,
        session_factory: Callable[..., AbstractContextManager[Session]],
        graph_rag: GraphRAG,
        agent: pydantic_ai.Agent,
        file_service: services.FileService,
        static_folder: Path,
    ):
        self.__agent = agent
        self.__session_factory = session_factory
        self.__graph_rag = graph_rag
        self.__file_service = file_service
        self.__static_folder = static_folder

    @property
    def __driver(self):
        return self.__graph_rag.retriever.driver

    @property
    def __database(self):
        return self.__graph_rag.retriever.neo4j_database

    # def __read_json_graph(self, filepath: Path) -> dict:
    #     if not filepath.exists():
    #         raise FileNotFoundError(f"Graph JSON file not found: {filepath}")
    #     if not filepath.is_file():
    #         raise ValueError(f"Provided path is not a file: {filepath}")

    #     return json.loads(filepath.read_text("utf-8"))

    # # === Flatten helper (to handle nested maps like progress_metric) ===
    # def __flatten_props(self, props: dict) -> dict:
    #     flat = {}
    #     for k, v in props.items():
    #         if isinstance(v, dict):
    #             # flatten maps like progress_metric
    #             for subk, subv in v.items():
    #                 flat[f"{k}_{subk}"] = subv
    #         elif isinstance(v, list):
    #             # flatten lists of simple values
    #             if all(isinstance(i, (str, int, float, bool)) for i in v):
    #                 flat[k] = v
    #             elif all(isinstance(i, dict) for i in v):
    #                 # for list of dicts that are not question_prompts
    #                 flat[k] = [json.dumps(i, ensure_ascii=False) for i in v]
    #             else:
    #                 flat[k] = str(v)
    #         else:
    #             flat[k] = v
    #     return flat

    # def __create_nodes_and_relationships(
    #     self,
    #     tx: ManagedTransaction,
    #     node: dict,
    #     parent_id: str | None = None,
    # ):
    #     node_id = node.get("id")
    #     if not node_id:
    #         raise ValueError(f"Node is missing 'id' field: {node}")
    #     if not isinstance(node_id, str):
    #         raise TypeError(f"Node 'id' must be a string in node: {node}")

    #     logger.debug(f"Creating node and relationships for node ID: {node_id}")

    #     node_label = "Concept"
    #     if node_id.startswith("P"):
    #         node_label = "Procedure"
    #     elif node_id.startswith("A"):
    #         node_label = "Assessment"

    #     # ✅ Flatten everything except children & connections
    #     props = self.__flatten_props(
    #         {
    #             k: v
    #             for k, v in node.items()
    #             if k not in ["children", "connections", "question_prompts"]
    #         }
    #     )

    #     # Create node
    #     tx.run(
    #         f"""
    #         MERGE (n:{node_label} {{id:$id}})
    #         SET n += $props
    #         """,
    #         id=node_id,
    #         props=props,
    #     )

    #     # === If Assessment has question_prompts, make Question nodes ===
    #     if node_label == "Assessment" and "question_prompts" in node:
    #         for idx, q in enumerate(node["question_prompts"], start=1):
    #             if isinstance(q, dict):
    #                 q_text = q.get("question", "")
    #             else:
    #                 q_text = str(q)
    #             q_id = f"{node_id}-Q{idx}"
    #             tx.run(
    #                 """
    #                 MERGE (q:Question {id:$qid})
    #                 SET q.text = $text
    #                 WITH q
    #                 MATCH (a {id:$aid})
    #                 MERGE (a)-[:HAS_QUESTION]->(q)
    #                 """,
    #                 qid=q_id,
    #                 text=q_text,
    #                 aid=node_id,
    #             )

    #     # === Create HAS_CHILD relationship if nested ===
    #     if parent_id:
    #         tx.run(
    #             """
    #             MATCH (p {id:$parent_id}), (c {id:$child_id})
    #             MERGE (p)-[:HAS_CHILD]->(c)
    #             """,
    #             parent_id=parent_id,
    #             child_id=node_id,
    #         )

    #     # === Create connections between concepts ===
    #     for conn in node.get("connections", []):
    #         if not isinstance(conn, dict):
    #             raise TypeError(
    #                 f"Was expecting connection to be a dict in node {node_id}, got: {type(conn)}"
    #             )
    #         if "to" not in conn:
    #             raise ValueError(
    #                 f"Connection missing 'to' field in node {node_id}: {conn}"
    #             )

    #         conn_relation = str(conn["relation"])
    #         conn_to = str(conn["to"])

    #         logger.debug(
    #             f"Creating connection from {node_id} to {conn_to} with relation {conn_relation}"
    #         )
    #         tx.run(
    #             f"""
    #             MATCH (a {{id:$from_id}}), (b {{id:$to_id}})
    #             MERGE (a)-[:{conn_relation}]->(b)
    #             """,
    #             from_id=node_id,
    #             to_id=conn_to,
    #         )

    #     # === Recurse for children ===
    #     logger.debug(f"Recursing into child node of {node_id}")
    #     for child in node.get("children", []):
    #         if not isinstance(child, dict):
    #             raise TypeError(
    #                 f"Was expecting child to be a dict in node {node_id}, got: {type(child)}"
    #             )
    #         self.__create_nodes_and_relationships(tx, child, parent_id=node_id)

    def get_knowledge(self, knowledge_id: str) -> models.RootKnowledge:
        @unit_of_work
        def txn_fn(tx: ManagedTransaction) -> models.RootKnowledge:
            query = """
            MATCH (root {id: $id})
            CALL {
                WITH root
                MATCH (root)-[:HAS_CHILD*0..]->(n)
                RETURN collect(distinct n) + root AS nodes
            }
            CALL {
                WITH nodes
                UNWIND nodes AS n
                OPTIONAL MATCH (n)-[:HAS_CHILD]->(c)
                WHERE c IN nodes
                RETURN collect(distinct {parent: n.id, child: c.id}) AS child_edges
            }
            CALL {
                WITH nodes
                UNWIND nodes AS n
                OPTIONAL MATCH (n)-[rel]->(m)
                WHERE m IN nodes AND type(rel) <> $child_rel
                RETURN collect(distinct {from: n.id, to: m.id, rel: type(rel)}) AS other_edges
            }
            RETURN nodes, child_edges, other_edges
            """
            result = tx.run(
                query, id=knowledge_id, child_rel=self.__child_relation_type
            )
            record = result.single()
            if not record or not record["nodes"]:
                raise ValueError(f"Knowledge with ID '{knowledge_id}' not found")

            nodes = record["nodes"]
            child_edges = record["child_edges"] or []
            other_edges = record["other_edges"] or []

            nodes_by_id: dict[str, dict] = {}
            for node in nodes:
                props = dict(node)
                if "id" not in props:
                    props["id"] = node.get("id")
                nodes_by_id[props["id"]] = {"props": props}

            children_map: dict[str, list[str]] = {}
            for edge in child_edges:
                parent_id = edge.get("parent")
                child_id = edge.get("child")
                if not parent_id or not child_id:
                    continue
                children_map.setdefault(parent_id, []).append(child_id)

            allowed_relations = {
                rel.value for rel in models.KnowledgeConceptualLinkType
            }
            connections_map: dict[str, list[dict]] = {}
            for edge in other_edges:
                relation = edge.get("rel")
                if relation not in allowed_relations:
                    continue
                from_id = edge.get("from")
                to_id = edge.get("to")
                if not from_id or not to_id:
                    continue
                connections_map.setdefault(from_id, []).append(
                    {"relation": relation, "to": to_id}
                )

            def build_node(node_id: str, path: set[str]) -> models.Knowledge:
                if node_id in path:
                    raise ValueError(
                        f"Cycle detected in knowledge tree at node '{node_id}'"
                    )
                node_info = nodes_by_id.get(node_id)
                if not node_info:
                    raise ValueError(
                        f"Node with ID '{node_id}' was not found in the subtree"
                    )

                path.add(node_id)
                props = dict(node_info["props"])
                node_type = props["type"]
                child_ids = sorted(children_map.get(node_id, []))

                if node_id == knowledge_id:
                    children = [build_node(cid, path) for cid in child_ids]
                    props["children"] = children
                    path.remove(node_id)
                    return models.RootKnowledge(**props)

                if node_type == models.KnowledgeType.PROCEDURAL.value:
                    child_node = None
                    if child_ids:
                        if len(child_ids) > 1:
                            logger.warning(
                                "Procedural node '%s' has multiple children; using the first",
                                node_id,
                            )
                        child_node = build_node(child_ids[0], path)
                    props["children"] = child_node
                    path.remove(node_id)
                    return models.ProceduralKnowledge(**props)

                if node_type == models.KnowledgeType.ASSESSMENT.value:
                    path.remove(node_id)
                    return models.AssessmentKnowledge(**props)

                stored_connections = props.get("connections") or []
                props["connections"] = stored_connections + connections_map.get(
                    node_id, []
                )
                props["children"] = [build_node(cid, path) for cid in child_ids]
                path.remove(node_id)
                return models.ConceptualKnowledge(**props)

            return build_node(knowledge_id, set())

        with self.__session_factory() as session:
            return session.execute_read(txn_fn)

    def create_knowledge_from_file(self, file_path: Path) -> str:
        textual = self.__file_service.extract_textual_content(file_path)
        visual = self.__file_service.extract_visual_content(file_path)
        user_prompt = f"""The following extracted content contains textual and OCR segments from the source material. 
        Use it to populate the JSON fields accurately:
        
        ## Extracted Textual Content:
        ```
        {textual}
        ```

        ## Extracted Visual Content:
        ```
        {visual}
        ```
        Remember to adhere strictly to the expected JSON structure for nodes and relationships, and ensure all relevant information from the extracted content is captured in the appropriate fields.
        """

        knowledge = self.__agent.run_sync(
            user_prompt, output_type=models.RootKnowledge
        ).output
        logger.debug(f"Generated knowledge from agent: {knowledge}")
        knowledge.override_conceptual_sources(
            file_path.relative_to(self.__static_folder).as_posix()
        )

        return self.create_knowledge(knowledge)

        # logger.info(f"Loading graph from file: {file_path}")
        # try:
        #     graph = self.__read_json_graph(file_path)
        #     with self.__session_factory() as session:
        #         session.execute_write(self.__create_nodes_and_relationships, graph)
        #     logger.info("Graph successfully loaded into Neo4j")
        # except Exception as e:
        #     logger.error(f"Error loading graph into Neo4j: {e}")
        #     raise

    def __create_assessment_knowledge_node(
        self,
        parent_id: str,
        item: models.AssessmentKnowledge,
        *,
        tx: ManagedTransaction,
    ) -> models.AssessmentKnowledge:
        query = (
            "MATCH (parent {id: $parent_id}) "
            "WHERE parent.type = $parent_type "
            "CREATE (n:Assessment $props) "
            f"MERGE (parent)-[:{self.__child_relation_type}]->(n) "
            "RETURN n"
        )
        result = tx.run(
            query,
            parent_id=parent_id,
            parent_type=models.KnowledgeType.ASSESSMENT.value,
            props=item.model_dump(by_alias=True, exclude={"children"}),
        )
        record = result.single()
        if not record:
            raise ValueError("Failed to create assessment node in Neo4j")
        return models.AssessmentKnowledge(**record["n"])

    def __create_procedural_knowledge_node(
        self,
        parent_id: str,
        item: models.ProceduralKnowledge,
        *,
        tx: ManagedTransaction,
    ) -> models.ProceduralKnowledge:
        query = (
            "MATCH (parent {id: $parent_id}) "
            "WHERE parent.type IN $parent_types "
            "CREATE (n:Procedure $props) "
            f"MERGE (parent)-[:{self.__child_relation_type}]->(n) "
            "RETURN n"
        )
        result = tx.run(
            query,
            parent_id=parent_id,
            parent_types=[
                models.KnowledgeType.CONCEPTUAL.value,
                models.KnowledgeType.PROCEDURAL.value,
            ],
            props=item.model_dump(by_alias=True, exclude={"children"}),
        )
        record = result.single()
        if not record:
            raise ValueError("Failed to create procedural node in Neo4j")
        return models.ProceduralKnowledge(**record["n"])

    def __create_conceptual_knowledge_node(
        self,
        parent_id: str,
        item: models.ConceptualKnowledge,
        *,
        tx: ManagedTransaction,
    ) -> models.ConceptualKnowledge:
        query = (
            "MATCH (parent {id: $parent_id}) "
            "WHERE parent.type = $parent_type "
            "CREATE (n:Concept $props) "
            f"MERGE (parent)-[:{self.__child_relation_type}]->(n) "
            "RETURN n"
        )
        result = tx.run(
            query,
            parent_id=parent_id,
            parent_type=item.type_.value,
            props=item.model_dump(by_alias=True, exclude={"children"}),
        )
        record = result.single()
        if not record:
            raise ValueError("Failed to create conceptual node in Neo4j")

        for conn in item.connections:
            tx.run(
                f"""
                MATCH (a {{id:$from_id}}), (b {{id:$to_id}})
                MERGE (a)-[:{conn.relation}]->(b)
                """,
                from_id=item.id,
                to_id=conn.to,
            )
        return models.ConceptualKnowledge(**record["n"])

    def __update_conceptual_knowledge_relationships(
        self,
        node_id: str,
        connections: list[models.ConceptualKnowledgeConnection],
        *,
        tx: ManagedTransaction,
    ) -> None:
        # === Validate that all target nodes exist before making any changes ===
        for conn in connections:
            result = tx.run("MATCH (n {id: $to_id}) RETURN n", to_id=conn.to)
            if not result.single():
                raise ValueError(
                    f"Target node with ID '{conn.to}' for connection not found"
                )

        # === Delete existing conceptual relationships from this node ===
        tx.run(
            """
            MATCH (n {id: $node_id})-[r]->(m)
            WHERE type(r) IN $allowed_rels
            DELETE r
            """,
            node_id=node_id,
            allowed_rels=[rel.value for rel in models.KnowledgeConceptualLinkType],
        )

        # === Create new relationships from this node to targets ===
        for conn in connections:
            tx.run(
                f"""
                    MATCH (a {{id:$from_id}}), (b {{id:$to_id}})
                    MERGE (a)-[:{conn.relation}]->(b)
                    """,
                from_id=node_id,
                to_id=conn.to,
            )

    def __create_root_knowledge_node(
        self,
        item: models.RootKnowledge,
        *,
        tx: ManagedTransaction,
    ) -> models.RootKnowledge:
        query = "CREATE (n:Concept $props) RETURN n"
        # TODO: Use a schema in future
        result = tx.run(
            query, props=item.model_dump(by_alias=True, exclude={"children"})
        )
        record = result.single()
        if not record:
            raise ValueError("Failed to create root node in Neo4j")
        return models.RootKnowledge(**record["n"])

    def __create_knowledge_graph(
        self,
        item: models.Knowledge,
        parent_id: str | None = None,
        *,
        tx: ManagedTransaction,
    ) -> str:

        logger.info(
            f"Creating knowledge node with name '{item.name}' and ID '{item.id}' under parent ID '{parent_id}'"
        )
        if isinstance(item, models.RootKnowledge):
            logger.debug("Creating root knowledge node")
            new_parent_id = self.__create_root_knowledge_node(item, tx=tx)
        elif isinstance(item, models.ConceptualKnowledge):
            logger.debug("Creating conceptual knowledge node")
            new_parent_id = self.__create_conceptual_knowledge_node(
                parent_id, item, tx=tx
            )
        elif isinstance(item, models.AssessmentKnowledge):
            logger.debug("Creating assessment knowledge node")
            new_parent_id = self.__create_assessment_knowledge_node(
                parent_id, item, tx=tx
            )
        elif isinstance(item, models.ProceduralKnowledge):
            logger.debug("Creating procedural knowledge node")
            new_parent_id = self.__create_procedural_knowledge_node(
                parent_id, item, tx=tx
            )
        else:
            raise TypeError(f"Unsupported knowledge type: {type(item)}")

        logger.info(f"Successfully created node with ID '{new_parent_id}' in Neo4j")
        logger.debug(
            f"Recursively creating child nodes for parent ID '{new_parent_id}'"
        )
        for child in item.children:
            self.__create_knowledge_graph(child, parent_id=new_parent_id, tx=tx)
        logger.debug(
            f"Finished creating all child nodes for parent ID '{new_parent_id}'"
        )

        return new_parent_id

    def create_knowledge(self, root: models.RootKnowledge) -> str:
        with self.__session_factory() as session:
            tx = session.begin_transaction()
            try:
                logger.info(
                    f"Starting creation of knowledge graph for root node '{root.name}'"
                )
                root_id = self.__create_knowledge_graph(root, tx=tx)
                logger.info(
                    f"Completed creation of knowledge graph with root ID '{root_id}'"
                )
                logger.debug(
                    f"Updating conceptual knowledge relationships for root ID '{root_id}'"
                )
                for child in root.children:
                    logger.debug(
                        f"Updating relationships for child node '{child.name}' with ID '{child.id}'"
                    )
                    self.__update_conceptual_knowledge_relationships(
                        child.id, child.connections, tx=tx
                    )
                logger.debug(
                    f"Finished updating relationships for all child nodes of root ID '{root_id}'"
                )
            except Exception as e:
                logger.error(f"Error creating knowledge graph: {e}")
                tx.rollback()
                raise
            else:
                tx.commit()
                return root_id

    # def reembed_nodes(self) -> None:
    #     logger.info("Re-embedding all nodes in Neo4j")
    #     with self.__session_factory() as session:
    #         query = """
    #         MATCH (n)
    #         WHERE n:Concept OR n:Procedure OR n:Assessment
    #         RETURN n.id AS id, n.name AS name, n.definition AS definition
    #         """
    #         records = list(session.run(query))
    #         logger.info(f"🔍 Found {len(records)} nodes to re-embed")
    #         id_query_map = {
    #             record["id"]: f"{record['name']} {record.get('definition','')}"
    #             for record in records
    #         }
    #         vectors = self.__embedder.embed_documents_sync(list(id_query_map.values()))
    #         ## TODO: Why not use the upsert_vectors function here, instead the loop with individual queries?
    #         upsert_vectors(
    #             self.__driver,
    #             id_query_map.keys(),
    #             self.__vector_property_name,
    #             vectors,
    #             self.__database,
    #         )
