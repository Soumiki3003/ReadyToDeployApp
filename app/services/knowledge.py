import logging
from datetime import datetime, timezone
from pathlib import Path
from contextlib import AbstractContextManager
from typing import Callable
from uuid import uuid4

import jinja2
import pydantic_ai
from neo4j import ManagedTransaction, Session, Transaction, unit_of_work

from app import models, schemas, services
from app.models.knowledge import Knowledge
from tests import factories


class KnowledgeUploadService:
    # TODO: For now it uses in memory database
    def __init__(self, db: dict[str, models.KnowledgeUploadRecord] = {}):
        self.__db = db
        self.__logger = logging.getLogger(__name__)

    def __get_now(self):
        return datetime.now(timezone.utc)

    def create(self, filepath: Path) -> str:
        self.__logger.info(f"Creating upload record for file: {filepath.name}")
        new_upload = models.KnowledgeUploadRecord(
            filepath=filepath, created_at=self.__get_now()
        )
        self.__db[new_upload.id] = new_upload
        self.__logger.debug(f"Upload record created with ID: {new_upload.id}")
        return new_upload.id

    def get(self, upload_id: str) -> models.KnowledgeUploadRecord:
        if upload_id not in self.__db:
            raise ValueError(f"Upload ID not found: {upload_id}")
        return self.__db[upload_id].model_copy(deep=True)

    def get_many(
        self, *, limit: int | None = 10, offset: int = 0
    ) -> list[models.KnowledgeUploadRecord]:
        if offset < 0:
            raise ValueError("Offset must be non-negative")
        if limit is not None and limit < 0:
            raise ValueError("Limit must be non-negative")

        items = list(self.__db.values())
        if offset:
            items = items[offset:]
        if limit is not None:
            items = items[:limit]
        return [item.model_copy(deep=True) for item in items]

    def __update(self, upload_id: str, data: dict) -> models.KnowledgeUploadRecord:
        if upload_id not in self.__db:
            raise ValueError(f"Upload ID not found: {upload_id}")
        for key, value in data.items():
            setattr(self.__db[upload_id], key, value)
        self.__db[upload_id].updated_at = self.__get_now()
        return self.__db[upload_id].model_copy(deep=True)

    def mark_as_processing(self, upload_id: str) -> models.KnowledgeUploadRecord:
        self.__logger.info(f"Marking upload {upload_id} as PROCESSING")
        return self.__update(
            upload_id, {"status": models.KnowledgeUploadStatus.PROCESSING}
        )

    def mark_as_completed(
        self, upload_id: str, *, knowledge_id: str | None = None
    ) -> models.KnowledgeUploadRecord:
        self.__logger.info(f"Marking upload {upload_id} as COMPLETED")
        data: dict[str, object] = {
            "status": models.KnowledgeUploadStatus.COMPLETED,
        }
        if knowledge_id:
            data["knowledge_id"] = knowledge_id
        return self.__update(upload_id, data)

    def mark_as_failed(
        self, upload_id: str, *, error: str
    ) -> models.KnowledgeUploadRecord:
        self.__logger.error(f"Marking upload {upload_id} as FAILED: {error}")
        return self.__update(
            upload_id,
            {"status": models.KnowledgeUploadStatus.FAILED, "error_message": error},
        )

    def delete(self, upload_id: str):
        if upload_id not in self.__db:
            raise ValueError(f"Upload ID not found: {upload_id}")
        del self.__db[upload_id]


class KnowledgeService:
    __uploads: dict[str, models.KnowledgeUploadRecord] = {}
    __child_relation_type = "HAS_CHILD"
    __teaches_rel_type = "TEACHES"
    __enrolled_rel_type = "ENROLLED_IN"
    __user_node_name = "User"

    def __init__(
        self,
        *,
        session_factory: Callable[..., AbstractContextManager[Session]],
        agent: pydantic_ai.Agent,
        file_service: services.FileService,
        upload_service: KnowledgeUploadService,
        static_folder: Path,
        template_env: jinja2.Environment,
        batch_size: int = 20,
        fake_generation: bool = False,
    ):
        self.__agent = agent
        self.__session_factory = session_factory
        self.__file_service = file_service
        self.__upload_service = upload_service
        self.__static_folder = static_folder
        self.__logger = logging.getLogger(__name__)
        self.__template_env = template_env
        self.__batch_size = batch_size
        self.__fake_generation = fake_generation

    def get_knowledge(self, knowledge_id: str) -> models.Knowledge:
        @unit_of_work()
        def txn_fn(tx: ManagedTransaction, knowledge_id: str) -> models.Knowledge:
            query = (
                "MATCH (root {id: $id, type: $root_type}) "
                "CALL { "
                "WITH root "
                f"MATCH (root)-[:{self.__child_relation_type}*0..]->(n) "
                "WITH root, collect(distinct n) AS descendants "
                "RETURN descendants + [root] AS nodes "
                "} "
                "CALL { "
                "WITH nodes "
                "UNWIND nodes AS n "
                f"OPTIONAL MATCH (n)-[:{self.__child_relation_type}]->(c) "
                "WHERE c IN nodes "
                "RETURN collect(distinct {parent: n.id, child: c.id}) AS child_edges "
                "} "
                "CALL { "
                "WITH nodes "
                "UNWIND nodes AS n "
                "OPTIONAL MATCH (n)-[rel]->(m) "
                f"WHERE m IN nodes AND type(rel) <> '{self.__child_relation_type}' "
                "RETURN collect(distinct {from: n.id, to: m.id, rel: type(rel)}) AS other_edges "
                "} "
                "RETURN nodes, child_edges, other_edges"
            )

            result = tx.run(
                query,
                id=knowledge_id,
                root_type=models.KnowledgeType.ROOT,
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

            def build_node(
                *,
                node_id: str,
                path: set[str],
                nodes_by_id: dict[str, dict],
            ) -> models.Knowledge:
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
                    children = [
                        build_node(node_id=cid, path=path, nodes_by_id=nodes_by_id)
                        for cid in child_ids
                    ]
                    props["children"] = children
                    path.remove(node_id)
                    return models.RootKnowledge(**props)

                if node_type == models.KnowledgeType.PROCEDURAL.value:
                    child_node = None
                    if child_ids:
                        if len(child_ids) > 1:
                            self.__logger.warning(
                                "Procedural node '%s' has multiple children; using the first",
                                node_id,
                            )
                        child_node = build_node(
                            node_id=child_ids[0], path=path, nodes_by_id=nodes_by_id
                        )
                    props["child"] = child_node
                    path.remove(node_id)
                    return models.ProceduralKnowledge(**props)

                if node_type == models.KnowledgeType.ASSESSMENT.value:
                    path.remove(node_id)
                    return models.AssessmentKnowledge(**props)

                stored_connections = props.get("connections") or []
                props["connections"] = stored_connections + connections_map.get(
                    node_id, []
                )
                props["children"] = [
                    build_node(node_id=cid, path=path, nodes_by_id=nodes_by_id)
                    for cid in child_ids
                ]
                path.remove(node_id)
                return models.ConceptualKnowledge(**props)

            return build_node(
                node_id=knowledge_id,
                path=set([]),
                nodes_by_id=nodes_by_id,
            )

        with self.__session_factory() as session:
            return session.execute_read(txn_fn, knowledge_id=knowledge_id)

    def get_root_nodes(
        self,
        limit: int | None = 5,
        offset: int = 0,
        user_id: str | None = None,
        user_role: str | None = None,
    ) -> list[schemas.KnowledgeRootNode]:
        if offset < 0:
            raise ValueError("Offset must be non-negative")
        if limit is not None and limit < 1:
            raise ValueError("Limit must be at least 1 when provided")

        if user_id and user_role == models.UserRole.INSTRUCTOR:
            match_clause = f"MATCH (u:{self.__user_node_name} {{id: $user_id}})-[:{self.__teaches_rel_type}]->(n {{type: $root_type}}) "
        elif user_id and user_role == models.UserRole.STUDENT:
            match_clause = f"MATCH (u:{self.__user_node_name} {{id: $user_id}})-[:{self.__enrolled_rel_type}]->(n {{type: $root_type}}) "
        else:
            match_clause = "MATCH (n {type: $root_type}) "

        query = (
            match_clause
            + "RETURN n.id AS id, n.name AS name, n.description AS description, n.sources AS sources "
            "ORDER BY coalesce(n.updated_at, n.created_at) DESC "
            "SKIP $offset " + ("LIMIT $limit" if limit is not None else "")
        )

        with self.__session_factory() as session:
            result = session.run(
                query,
                root_type=models.KnowledgeType.ROOT,
                offset=offset,
                limit=limit,
                user_id=user_id,
            ).data()
        return [
            schemas.KnowledgeRootNode(
                id=record["id"],
                name=record.get("name"),
                description=record.get("description"),
                sources=record.get("sources") or [],
            )
            for record in result
        ]

    def __process_pages_batch(
        self,
        upload_id: str,
        file_path: Path,
    ):
        self.__logger.debug("Extracting textual content...")
        textual = self.__file_service.extract_textual_content(file_path)
        self.__logger.debug(f"Extracted {len(textual)} textual content entries")

        self.__logger.debug("Extracting visual content...")
        visual = self.__file_service.extract_visual_content(file_path)
        self.__logger.debug(f"Extracted {len(visual)} visual content entries")

        root_knowledge = models.RootKnowledge(sources=[upload_id])
        self.__upload_service.mark_as_processing(upload_id)
        self.__logger.info("Running AI agent to generate knowledge graph...")

        for batch in range(0, len(textual), self.__batch_size):
            batch_text = textual[batch : batch + self.__batch_size]
            batch_visual = visual[batch : batch + self.__batch_size]
            page_nums = list(range(batch, batch + self.__batch_size))
            page_list = [
                {"text": text, "visual": visual, "page_num": num}
                for text, visual, num in zip(batch_text, batch_visual, page_nums)
            ]
            user_prompt = self.__template_env.get_template(
                "knowledge_user_prompt.j2"
            ).render(
                source_filename=file_path.name,
                page_list=page_list,
                root_knowledge=root_knowledge.model_dump_json(by_alias=True),
            )
            self.__logger.info(f"Processing pages {page_nums[0]}-{page_nums[-1]}...")
            root_knowledge = self.__agent.run_sync(
                user_prompt, output_type=models.RootKnowledge
            ).output
            self.__logger.info(
                f"Processing pages {page_nums[0]}-{page_nums[-1]} complete."
            )

        return root_knowledge

    def create_knowledge_from_file(self, file_path: Path) -> str:
        self.__logger.info(f"Starting knowledge creation from file: {file_path.name}")
        upload_id = self.__upload_service.create(file_path)
        if self.__fake_generation:
            self.__logger.warning(
                "Fake generation enabled - using factory to create knowledge graph"
            )
            root_knowledge = factories.RootKnowledgeFactory.build()
        else:
            root_knowledge = self.__process_pages_batch(upload_id, file_path)

        try:
            self.__logger.info("Processing all pages complete.")
            relative_path = file_path.relative_to(self.__static_folder).as_posix()
            self.__logger.debug(f"Setting source to: {relative_path}")
            root_knowledge.override_conceptual_sources(relative_path)

            self.__logger.info("Creating knowledge graph in Neo4j...")
            knowledge_id = self.create_knowledge(root_knowledge)
            self.__logger.info(
                f"Knowledge graph created successfully with ID: {knowledge_id}"
            )
            self.__upload_service.mark_as_completed(
                upload_id,
                knowledge_id=knowledge_id,
            )
            return knowledge_id
        except Exception as e:
            self.__logger.error(
                f"Error creating knowledge from file {file_path.name}: {e}",
                exc_info=True,
            )
            self.__upload_service.mark_as_failed(upload_id, error=str(e))
            raise

    def create_empty_course(
        self,
        name: str,
        description: str = "",
        instructor_ids: list[str] | None = None,
        student_ids: list[str] | None = None,
    ) -> str:
        self.__logger.info(f"Creating empty course: {name}")
        root_knowledge = models.RootKnowledge(
            name=name,
            description=description,
            sources=[],
        )
        knowledge_id = self.create_knowledge(root_knowledge)

        if instructor_ids:
            self.set_course_instructors(knowledge_id, instructor_ids)
        if student_ids:
            self.set_course_students(knowledge_id, student_ids)

        self.__logger.info(f"Empty course created with ID: {knowledge_id}")
        return knowledge_id

    def add_document_to_course(self, course_id: str, file_path: Path) -> str:
        self.__logger.info(f"Adding document {file_path.name} to course {course_id}")
        upload_id = self.__upload_service.create(file_path)

        if self.__fake_generation:
            self.__logger.warning(
                "Fake generation enabled - using factory to create knowledge graph"
            )
            new_root = factories.RootKnowledgeFactory.build()
        else:
            new_root = self.__process_pages_batch(upload_id, file_path)

        try:
            relative_path = file_path.relative_to(self.__static_folder).as_posix()

            def merge_txn(tx):
                # Verify root exists
                check = tx.run(
                    "MATCH (n {id: $id, type: $root_type}) RETURN n.id AS id",
                    id=course_id,
                    root_type=models.KnowledgeType.ROOT.value,
                )
                if not check.single():
                    raise ValueError(f"Course with ID {course_id} not found")

                # Add new conceptual children to existing root
                for child in new_root.children:
                    child.source = relative_path
                    self.__create_knowledge_graph(child, parent_id=course_id, tx=tx)
                # Append source to root's sources list
                tx.run(
                    "MATCH (n {id: $id, type: $root_type}) "
                    "SET n.sources = CASE "
                    "  WHEN n.sources IS NULL THEN [$source] "
                    "  WHEN NOT $source IN n.sources THEN n.sources + $source "
                    "  ELSE n.sources "
                    "END",
                    id=course_id,
                    root_type=models.KnowledgeType.ROOT.value,
                    source=relative_path,
                )

            with self.__session_factory() as session:
                session.execute_write(merge_txn)

            self.__upload_service.mark_as_completed(upload_id, knowledge_id=course_id)
            self.__logger.info(f"Document {file_path.name} added to course {course_id}")
            return course_id
        except Exception as e:
            self.__logger.error(
                f"Error adding document to course {course_id}: {e}",
                exc_info=True,
            )
            self.__upload_service.mark_as_failed(upload_id, error=str(e))
            raise

    def __create_assessment_knowledge_node(
        self,
        parent_id: str,
        item: models.AssessmentKnowledge,
        *,
        tx: Transaction,
    ) -> models.AssessmentKnowledge:
        query = (
            "MATCH (parent {id: $parent_id}) "
            "WHERE parent.type = $parent_type "
            f"CREATE (n:{models.KnowledgeType.ASSESSMENT} $props) "
            f"MERGE (parent)-[:{self.__child_relation_type}]->(n) "
            "RETURN n"
        )
        result = tx.run(
            query,
            parent_id=parent_id,
            parent_type=models.KnowledgeType.CONCEPTUAL.value,
            props=item.model_dump(mode="json", by_alias=True, exclude={"children"}),
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
        tx: Transaction,
    ) -> models.ProceduralKnowledge:
        query = (
            "MATCH (parent {id: $parent_id}) "
            "WHERE parent.type IN $parent_types "
            f"CREATE (n:{models.KnowledgeType.PROCEDURAL} $props) "
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
            props=item.model_dump(
                mode="json", by_alias=True, exclude={"children", "child"}
            ),
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
        tx: Transaction,
    ) -> models.ConceptualKnowledge:
        # TODO: neo4j.exceptions.CypherSyntaxError: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'child_relation_type': expected '(', 'ALL' or 'ANY' (line 1, column 110 (offset: 109))
        # "MATCH (parent {id: $parent_id}) WHERE parent.type = $parent_type CREATE (n:Concept $props) MERGE (parent)-[:$child_relation_type]->(n) RETURN n"
        #                                                                                                               ^} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}
        query = (
            "MATCH (parent {id: $parent_id}) "
            "WHERE parent.type = $parent_type "
            f"CREATE (n:{models.KnowledgeType.CONCEPTUAL} $props) "
            f"MERGE (parent)-[:{self.__child_relation_type}]->(n) "
            "RETURN n"
        )

        item_props = item.model_dump(
            mode="json", by_alias=True, exclude={"children", "connections"}
        )
        try:
            self.__logger.debug(
                f"Creating conceptual node with parent_id={parent_id}, "
                f"parent_type={item.type_.value}, props={item_props}"
            )
            result = tx.run(
                query,
                parent_id=parent_id,
                parent_type=models.KnowledgeType.ROOT.value,
                props=item_props,
            )
            record = result.single()
            if not record:
                self.__logger.error(
                    f"Query returned no results. Parent with id={parent_id} and type={item.type_.value} may not exist"
                )
                raise ValueError(
                    f"Failed to create conceptual node in Neo4j. Parent node not found: id={parent_id}, type={item.type_.value}"
                )
        except Exception as e:
            self.__logger.error(
                f"Error creating conceptual node with parent_id={parent_id}, "
                f"parent_type={item.type_.value}, props={item_props}: {e}",
                exc_info=True,
            )
            raise

        return models.ConceptualKnowledge(**record["n"])

    def __update_conceptual_knowledge_relationships(
        self,
        node_id: str,
        connections: list[models.ConceptualKnowledgeConnection],
        *,
        tx: Transaction,
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
            conn_query = (
                "MATCH (a {id:$from_id}), (b {id:$to_id}) "
                f"MERGE (a)-[:{conn.relation.value}]->(b) "
            )
            tx.run(
                conn_query,
                from_id=node_id,
                to_id=conn.to,
            )

    def __create_root_knowledge_node(
        self,
        item: models.RootKnowledge,
        *,
        tx: Transaction,
    ) -> models.RootKnowledge:
        query = f"CREATE (n:{models.KnowledgeType.ROOT.value} $props) RETURN n"
        # TODO: Use a schema in future
        result = tx.run(
            query,
            props=item.model_dump(mode="json", by_alias=True, exclude={"children"}),
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
        tx: Transaction,
    ) -> Knowledge:
        self.__logger.info(
            f"Creating knowledge node with name '{item.name}' and ID '{item.id}' under parent ID '{parent_id}'"
        )
        if isinstance(item, models.RootKnowledge):
            self.__logger.debug("Creating root knowledge node")
            new_parent = self.__create_root_knowledge_node(item, tx=tx)
        else:
            if parent_id is None:
                raise ValueError("Parent ID is required for non-root knowledge nodes")
            if isinstance(item, models.ConceptualKnowledge):
                self.__logger.debug("Creating conceptual knowledge node")
                new_parent = self.__create_conceptual_knowledge_node(
                    parent_id, item, tx=tx
                )
            elif isinstance(item, models.AssessmentKnowledge):
                self.__logger.debug("Creating assessment knowledge node")
                new_parent = self.__create_assessment_knowledge_node(
                    parent_id, item, tx=tx
                )
            elif isinstance(item, models.ProceduralKnowledge):
                self.__logger.debug("Creating procedural knowledge node")
                new_parent = self.__create_procedural_knowledge_node(
                    parent_id, item, tx=tx
                )
            else:
                raise TypeError(f"Unsupported knowledge type: {type(item)}")

        self.__logger.info(
            f"Successfully created node with ID '{new_parent.id}' in Neo4j"
        )
        self.__logger.debug(
            f"Recursively creating child nodes for parent ID '{new_parent.id}'"
        )

        if isinstance(item, models.ProceduralKnowledge):
            item_children = [item.child] if item.child else []
        elif not isinstance(item, models.AssessmentKnowledge):
            item_children = item.children
        else:
            item_children = []

        for child in item_children:
            self.__create_knowledge_graph(child, parent_id=new_parent.id, tx=tx)
        self.__logger.debug(
            f"Finished creating all child nodes for parent ID '{new_parent.id}'"
        )

        return new_parent

    def __get_all_ids_recursive(self, node: models.Knowledge) -> list[str]:
        ids = [node.id]

        if isinstance(node, models.ProceduralKnowledge) and node.child:
            ids.extend(self.__get_all_ids_recursive(node.child))
        elif isinstance(node, (models.ConceptualKnowledge, models.RootKnowledge)):
            for child in node.children:
                ids.extend(self.__get_all_ids_recursive(child))

        return ids

    def delete_course(self, course_id: str) -> None:
        """Delete a root node and all its descendants entirely."""
        self.__logger.info(f"Deleting course {course_id} and all descendants")

        def txn_fn(tx):
            check = tx.run(
                "MATCH (n {id: $id, type: $root_type}) RETURN n.id AS id",
                id=course_id,
                root_type=models.KnowledgeType.ROOT.value,
            )
            if not check.single():
                raise ValueError(f"Course with ID {course_id} not found")

            # Delete all descendants first
            tx.run(
                f"MATCH (root {{id: $id, type: $root_type}})-[:{self.__child_relation_type}*1..]->(descendant) "
                "DETACH DELETE descendant",
                id=course_id,
                root_type=models.KnowledgeType.ROOT.value,
            )

            # Delete the root node itself
            tx.run(
                "MATCH (n {id: $id, type: $root_type}) DETACH DELETE n",
                id=course_id,
                root_type=models.KnowledgeType.ROOT.value,
            )

        with self.__session_factory() as session:
            session.execute_write(txn_fn)

        self.__logger.info(f"Course {course_id} deleted successfully")

    def clear_course(self, course_id: str) -> None:
        """Delete all children of a root node, keeping the root itself."""
        self.__logger.info(f"Clearing all children from course {course_id}")

        def txn_fn(tx):
            # Verify root exists
            check = tx.run(
                "MATCH (n {id: $id, type: $root_type}) RETURN n.id AS id",
                id=course_id,
                root_type=models.KnowledgeType.ROOT.value,
            )
            if not check.single():
                raise ValueError(f"Course with ID {course_id} not found")

            # Delete all descendant nodes and their relationships
            tx.run(
                f"MATCH (root {{id: $id, type: $root_type}})-[:{self.__child_relation_type}*1..]->(descendant) "
                "DETACH DELETE descendant",
                id=course_id,
                root_type=models.KnowledgeType.ROOT.value,
            )

            # Clear sources list on the root node
            tx.run(
                "MATCH (n {id: $id, type: $root_type}) SET n.sources = []",
                id=course_id,
                root_type=models.KnowledgeType.ROOT.value,
            )

        with self.__session_factory() as session:
            session.execute_write(txn_fn)

        self.__logger.info(f"Course {course_id} cleared successfully")

    def __set_course_relationship(
        self, course_id: str, user_ids: list[str], rel_type: str
    ) -> None:
        def txn_fn(tx):
            tx.run(
                f"MATCH (u:{self.__user_node_name})-[r:{rel_type}]->(n {{id: $course_id, type: $root_type}}) DELETE r",
                course_id=course_id,
                root_type=models.KnowledgeType.ROOT.value,
            )
            if user_ids:
                tx.run(
                    f"MATCH (n {{id: $course_id, type: $root_type}}) "
                    "UNWIND $user_ids AS uid "
                    f"MATCH (u:{self.__user_node_name} {{id: uid}}) "
                    f"CREATE (u)-[:{rel_type}]->(n)",
                    course_id=course_id,
                    root_type=models.KnowledgeType.ROOT.value,
                    user_ids=user_ids,
                )

        with self.__session_factory() as session:
            session.execute_write(txn_fn)

    def set_course_instructors(self, course_id: str, instructor_ids: list[str]) -> None:
        """Replace all TEACHES relationships for a course with the given instructor IDs."""
        self.__logger.info(
            f"Setting instructors for course {course_id}: {instructor_ids}"
        )
        self.__set_course_relationship(
            course_id, instructor_ids, self.__teaches_rel_type
        )

    def set_course_students(self, course_id: str, student_ids: list[str]) -> None:
        """Replace all ENROLLED_IN relationships for a course with the given student IDs."""
        self.__logger.info(f"Setting students for course {course_id}: {student_ids}")
        self.__set_course_relationship(course_id, student_ids, self.__enrolled_rel_type)

    def __get_course_users_by_rel(
        self, course_id: str, rel_type: str
    ) -> list[schemas.CourseMember]:
        with self.__session_factory() as session:
            result = session.run(
                f"MATCH (u:{self.__user_node_name})-[:{rel_type}]->(n {{id: $course_id, type: $root_type}}) "
                "RETURN u.id AS id, u.name AS name, u.email AS email, u.role AS role",
                course_id=course_id,
                root_type=models.KnowledgeType.ROOT.value,
            ).data()
        return [schemas.CourseMember(**r) for r in result]

    def get_course_members(
        self, course_id: str
    ) -> dict[str, list[schemas.CourseMember]]:
        """Get all instructors and students for a course."""
        instructors = self.__get_course_users_by_rel(course_id, self.__teaches_rel_type)
        students = self.__get_course_users_by_rel(course_id, self.__enrolled_rel_type)

        return {
            "instructors": instructors,
            "students": students,
        }

    def create_knowledge(self, root: models.RootKnowledge) -> str:
        with self.__session_factory() as session:
            tx = session.begin_transaction()
            try:
                self.__logger.info(
                    f"Starting creation of knowledge graph for root node '{root.name}'"
                )
                created_root = self.__create_knowledge_graph(root, tx=tx)
                self.__logger.debug(
                    f"Updating conceptual knowledge relationships for root ID '{created_root.id}'"
                )
                for child in root.children:
                    self.__logger.debug(
                        f"Updating relationships for child node '{child.name}' with ID '{child.id}'"
                    )
                    self.__update_conceptual_knowledge_relationships(
                        child.id, child.connections, tx=tx
                    )
                self.__logger.debug(
                    f"Finished updating relationships for all child nodes of root ID '{created_root.id}'"
                )
            except Exception as e:
                self.__logger.error(f"Error creating knowledge graph: {e}")
                tx.rollback()
                raise
            else:
                tx.commit()
                self.__logger.info(
                    f"Completed creation of knowledge graph with root ID '{created_root.id}'"
                )

        return created_root.id

    def update_node(self, node_id: str, updates: dict) -> None:
        """Update properties of a single node (any type)."""
        self.__logger.info(f"Updating node {node_id} with {list(updates.keys())}")

        props = {k: v for k, v in updates.items() if v is not None}
        if not props:
            return

        @unit_of_work()
        def txn_fn(tx: ManagedTransaction, *, node_id: str, props: dict) -> None:
            check = tx.run("MATCH (n {id: $id}) RETURN n.type AS type", id=node_id)
            if not check.single():
                raise ValueError(f"Node with ID '{node_id}' not found")

            tx.run("MATCH (n {id: $id}) SET n += $props", id=node_id, props=props)

        with self.__session_factory() as session:
            session.execute_write(txn_fn, node_id=node_id, props=props)

        self.__logger.info(f"Node {node_id} updated successfully")

    def delete_node(self, node_id: str, course_id: str) -> None:
        """Delete a node and its entire subtr ee. Cannot delete root nodes."""
        self.__logger.info(
            f"Deleting node {node_id} (and subtree) from course {course_id}"
        )
        child_rel = self.__child_relation_type

        @unit_of_work()
        def txn_fn(tx: ManagedTransaction, *, node_id: str) -> None:
            check = tx.run("MATCH (n {id: $id}) RETURN n.type AS type", id=node_id)
            record = check.single()
            if not record:
                raise ValueError(f"Node with ID '{node_id}' not found")
            if record["type"] == models.KnowledgeType.ROOT.value:
                raise ValueError(
                    "Cannot delete root node via this endpoint. "
                    "Use delete_course instead."
                )

            tx.run(
                f"MATCH (n {{id: $id}})-[:{child_rel}*1..]->(desc) DETACH DELETE desc",
                id=node_id,
            )
            tx.run("MATCH (n {id: $id}) DETACH DELETE n", id=node_id)

        with self.__session_factory() as session:
            session.execute_write(txn_fn, node_id=node_id)

        self.__logger.info(f"Node {node_id} deleted successfully")

    def add_child_node(
        self,
        parent_id: str,
        child_type: str,
        props: dict,
    ) -> str:
        """Create a new child node under the given parent and return its ID."""
        node_id = str(uuid4())
        props["id"] = node_id
        props["type"] = child_type
        self.__logger.info(f"Adding {child_type} child node under parent {parent_id}")
        child_rel = self.__child_relation_type

        @unit_of_work()
        def txn_fn(
            tx: ManagedTransaction,
            *,
            parent_id: str,
            child_type: str,
            props: dict,
        ) -> None:
            check = tx.run("MATCH (p {id: $id}) RETURN p.type AS type", id=parent_id)
            record = check.single()
            if not record:
                raise ValueError(f"Parent node with ID '{parent_id}' not found")

            parent_type = record["type"]
            valid_children: dict[str, list[str]] = {
                models.KnowledgeType.ROOT.value: [
                    models.KnowledgeType.CONCEPTUAL.value
                ],
                models.KnowledgeType.CONCEPTUAL.value: [
                    models.KnowledgeType.PROCEDURAL.value,
                    models.KnowledgeType.ASSESSMENT.value,
                ],
                models.KnowledgeType.PROCEDURAL.value: [
                    models.KnowledgeType.PROCEDURAL.value
                ],
            }
            allowed = valid_children.get(parent_type, [])
            if child_type not in allowed:
                raise ValueError(
                    f"Cannot add {child_type} child to {parent_type} parent. "
                    f"Allowed: {allowed}"
                )

            tx.run(
                "MATCH (p {id: $parent_id}) "
                "CREATE (n $props) "
                f"MERGE (p)-[:{child_rel}]->(n)",
                parent_id=parent_id,
                props=props,
            )

        with self.__session_factory() as session:
            session.execute_write(
                txn_fn, parent_id=parent_id, child_type=child_type, props=props
            )

        self.__logger.info(f"Child node {node_id} created successfully")
        return node_id

    def add_relationship(self, from_id: str, to_id: str, relation: str) -> None:
        """Add a conceptual relationship between two existing nodes."""
        self.__logger.info(f"Adding relationship {from_id} -[{relation}]-> {to_id}")

        allowed = {r.value for r in models.KnowledgeConceptualLinkType}
        if relation not in allowed:
            raise ValueError(f"Invalid relation type '{relation}'. Allowed: {allowed}")

        @unit_of_work()
        def txn_fn(
            tx: ManagedTransaction, *, from_id: str, to_id: str, relation: str
        ) -> None:
            for nid in (from_id, to_id):
                check = tx.run("MATCH (n {id: $id}) RETURN n.id", id=nid)
                if not check.single():
                    raise ValueError(f"Node with ID '{nid}' not found")

            tx.run(
                f"MATCH (a {{id: $from_id}}), (b {{id: $to_id}}) "
                f"MERGE (a)-[:{relation}]->(b)",
                from_id=from_id,
                to_id=to_id,
            )

        with self.__session_factory() as session:
            session.execute_write(
                txn_fn, from_id=from_id, to_id=to_id, relation=relation
            )

        self.__logger.info(f"Relationship {relation} created successfully")

    def update_relationship(
        self, from_id: str, to_id: str, old_relation: str, new_relation: str
    ) -> None:
        """Change the type of an existing conceptual relationship."""
        self.__logger.info(
            f"Updating relationship {from_id} -[{old_relation}]-> {to_id} to {new_relation}"
        )

        allowed = {r.value for r in models.KnowledgeConceptualLinkType}
        for rel in (old_relation, new_relation):
            if rel not in allowed:
                raise ValueError(f"Invalid relation type '{rel}'. Allowed: {allowed}")

        @unit_of_work()
        def txn_fn(
            tx: ManagedTransaction,
            *,
            from_id: str,
            to_id: str,
            old_relation: str,
            new_relation: str,
        ) -> None:
            for nid in (from_id, to_id):
                check = tx.run("MATCH (n {id: $id}) RETURN n.id", id=nid)
                if not check.single():
                    raise ValueError(f"Node with ID '{nid}' not found")

            tx.run(
                f"MATCH (a {{id: $from_id}})-[r:{old_relation}]->(b {{id: $to_id}}) "
                "DELETE r",
                from_id=from_id,
                to_id=to_id,
            )
            tx.run(
                f"MATCH (a {{id: $from_id}}), (b {{id: $to_id}}) "
                f"MERGE (a)-[:{new_relation}]->(b)",
                from_id=from_id,
                to_id=to_id,
            )

        with self.__session_factory() as session:
            session.execute_write(
                txn_fn,
                from_id=from_id,
                to_id=to_id,
                old_relation=old_relation,
                new_relation=new_relation,
            )

        self.__logger.info(f"Relationship updated to {new_relation} successfully")

    def delete_relationship(self, from_id: str, to_id: str, relation: str) -> None:
        """Delete a conceptual relationship between two existing nodes."""
        self.__logger.info(f"Deleting relationship {from_id} -[{relation}]-> {to_id}")

        allowed = {r.value for r in models.KnowledgeConceptualLinkType}
        if relation not in allowed:
            raise ValueError(f"Invalid relation type '{relation}'. Allowed: {allowed}")

        @unit_of_work()
        def txn_fn(
            tx: ManagedTransaction, *, from_id: str, to_id: str, relation: str
        ) -> None:
            for nid in (from_id, to_id):
                check = tx.run("MATCH (n {id: $id}) RETURN n.id", id=nid)
                if not check.single():
                    raise ValueError(f"Node with ID '{nid}' not found")

            tx.run(
                f"MATCH (a {{id: $from_id}})-[r:{relation}]->(b {{id: $to_id}}) "
                "DELETE r",
                from_id=from_id,
                to_id=to_id,
            )

        with self.__session_factory() as session:
            session.execute_write(
                txn_fn, from_id=from_id, to_id=to_id, relation=relation
            )

        self.__logger.info(f"Relationship {relation} deleted successfully")
