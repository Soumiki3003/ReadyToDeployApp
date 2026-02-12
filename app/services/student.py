import logging
from contextlib import AbstractContextManager
from typing import Callable

from neo4j import Session, unit_of_work
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.indexes import create_fulltext_index, create_vector_index
from pydantic_ai import Embedder

from app import gateways, models, schemas
from app.utils import hash_string

from .auth import AuthService

logger = logging.getLogger(__name__)


class StudentService:
    __student_node_name = "Student"

    __trajectory_node_name = "StudentTrajectory"
    __trajectory_query_hash_field = "query_hash"
    __trajectory_query_vector_field = "query_vector"

    __trajectory_rel_name = "HAS_TRAJECTORY"
    __trajectory_prev_rel_name = "PREVIOUS_TRAJECTORY"

    def __init__(
        self,
        session: Session,
        embedder: Embedder,
        rag: GraphRAG,
        auth_service: AuthService,
    ):
        self.__session = session
        self.__embedder = embedder
        self.__auth_service = auth_service
        self.__rag = rag

    def create_student(self, item: schemas.CreateStudent) -> models.Student:
        @unit_of_work()
        def tx_fn(tx: Session, item: schemas.CreateStudent) -> models.Student:
            password_hash = self.__auth_service.hash_password(item.password)
            item.password = password_hash

            query = f"""
            CREATE (s:{self.__student_node_name} {{name: $name, email: $email, password: $password, enabled: $enabled}})
            RETURN s
            """

            result = tx.run(query, item.model_dump(by_alias=True))
            node = result.single(strict=True)
            return models.Student(**node["s"])

        user_by_email = self.get_student_by_email(item.email)
        if user_by_email:
            raise ValueError(f"Student with email {item.email} already exists")

        new_user = self.__session.execute_write(tx_fn, item)
        return new_user

    def get_student(self, id: int) -> models.Student | None:
        @unit_of_work()
        def tx_fn(tx: Session, id: int) -> models.Student | None:
            query = f"MATCH (s:{self.__student_node_name}) WHERE id(s) = $id RETURN s"
            result = tx.run(query, id=id)
            record = result.single()
            if record:
                return models.Student(**record["s"])
            return None

        return self.__session.execute_read(tx_fn, id)

    def get_student_by_email(self, email: str) -> models.Student | None:
        @unit_of_work()
        def tx_fn(tx: Session, email: str) -> models.Student | None:
            query = (
                f"MATCH (s:{self.__student_node_name}) WHERE s.email = $email RETURN s"
            )
            result = tx.run(query, email=email)
            record = result.single()
            if record:
                return models.Student(**record["s"])
            return None

        return self.__session.execute_read(tx_fn, email)

    def update_student(
        self,
        id: int,
        *,
        to_update: schemas.UpdateStudent,
    ) -> models.Student:
        @unit_of_work()
        def tx_fn(
            tx: Session, id: int, to_update: schemas.UpdateStudent
        ) -> models.Student:
            params = to_update.model_dump(exclude_unset=True, by_alias=True)
            query = f"""
            MATCH (s:{self.__student_node_name}) WHERE id(s) = $id
            SET s += $props
            RETURN s
            """
            result = tx.run(query, id=id, props=params)
            node = result.single(strict=True)
            return models.Student(**node["s"])

        return self.__session.execute_write(tx_fn, id, to_update)

    def get_student_trajectory(self, student_id: int) -> list[models.StudentTrajectory]:
        @unit_of_work()
        def tx_fn(tx: Session, student_id: int) -> list[models.StudentTrajectory]:
            query = f"""
            MATCH (s:{self.__student_node_name})-[:{self.__trajectory_rel_name}]->(t:{self.__trajectory_node_name})
            WHERE id(s) = $student_id
            RETURN t, id(s) AS student_id
            ORDER BY t.timestamp DESC
            """
            result = tx.run(query, student_id=student_id)
            trajectories = []
            for record in result:
                data = dict(record["t"])
                data["student_id"] = record["student_id"]
                trajectories.append(models.StudentTrajectory(**data))
            return trajectories

        return self.__session.execute_read(tx_fn, student_id)

    def get_student_trajectory_by_query_exact_match(
        self,
        student_id: int,
        query: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[models.StudentTrajectory]:
        @unit_of_work()
        def tx_fn(
            tx: Session,
            student_id: int,
            query: str,
            limit: int | None = None,
            offset: int | None = None,
        ) -> list[models.StudentTrajectory]:

            statement = f"""
            MATCH (s:{self.__student_node_name})-[:{self.__trajectory_rel_name}]->(t:{self.__trajectory_node_name})
            WHERE id(s) = $student_id AND t.{self.__trajectory_query_hash_field} = $query_hash
            """
            if limit is not None:
                statement += " LIMIT $limit"
            if offset is not None:
                statement += " SKIP $offset"
            statement += " RETURN t, id(s) AS student_id ORDER BY t.timestamp DESC"

            result = tx.run(
                statement,
                student_id=student_id,
                query_hash=hash_string(query),
                limit=limit,
                offset=offset,
            )
            trajectories = []
            for record in result:
                data = dict(record["t"])
                data["student_id"] = record["student_id"]
                trajectories.append(models.StudentTrajectory(**data))
            return trajectories

        return self.__session.execute_read(
            tx_fn, student_id, query, limit=limit, offset=offset
        )

    def get_student_trajectory_by_query_similarity(
        self,
        student_id: int,
        query: str,
        *,
        threshold: float | None = None,
        limit: int | None = None,
    ) -> list[models.StudentTrajectory]:
        config = {}
        if limit is not None:
            config["top_k"] = limit
        if threshold is not None:
            config["similarity_threshold"] = threshold
        try:
            result = self.__rag.retriever.get_search_results(
                query_text=query,
                retriever_config=config,
                filters={"student_id": student_id},
            )
            return [models.StudentTrajectory(**item.data()) for item in result.records]
        except Exception as e:
            logger.warning(
                f"Vector retriever search failed during similarity retrieval: {e}"
            )
            return []

    def add_trajectory_entry(
        self,
        student_id: int,
        trajectory_entry: models.StudentTrajectory,
    ) -> models.StudentTrajectory:
        @unit_of_work()
        def tx_fn(
            tx: Session,
            student_id: int,
            trajectory_entry: models.StudentTrajectory,
        ) -> models.StudentTrajectory:
            query = f"""
            MATCH (s:{self.__student_node_name}) WHERE id(s) = $student_id
            CREATE (t:{self.__trajectory_node_name} {{student_id: $student_id, timestamp: $timestamp, query: $query, query_hash: $query_hash, query_vector: $query_vector, retrieved_nodes: $retrieved_nodes, scores: $scores, interaction_type: $interaction_type, query_repeat_count: $query_repeat_count, node_entry_count: $node_entry_count, response_time_sec: $response_time_sec, hint_triggered: $hint_triggered, hint_reason: $hint_reason, hint_text: $hint_text}})
            CREATE (s)-[rel:{self.__trajectory_rel_name}]->(t)
            WITH s, t, rel
            OPTIONAL MATCH (s)-[prev_rel:{self.__trajectory_rel_name}]->(prev_t:{self.__trajectory_node_name})
            WHERE prev_t <> t
            ORDER BY prev_t.timestamp DESC
            LIMIT 1
            CREATE (t)-[:{self.__trajectory_prev_rel_name}]->(prev_t)
            RETURN t, id(s) AS student_id
            """
            params = trajectory_entry.model_dump(by_alias=True)
            params[self.__trajectory_query_hash_field] = hash_string(
                trajectory_entry.query
            )
            params[self.__trajectory_query_vector_field] = (
                self.__embedder.embed_documents_sync([trajectory_entry.query])[0]
            )

            result = tx.run(query, student_id=student_id, **params)
            node = result.single(strict=True)
            data = dict(node["t"])
            data["student_id"] = node["student_id"]
            return models.StudentTrajectory(**data)

        # create_fulltext_index(
        #     self.__gateway.driver,
        #     f"idx-{self.__trajectory_node_name}-{self.__trajectory_query_hash_field}",
        #     self.__trajectory_node_name,
        #     [self.__trajectory_query_hash_field],
        # )

        # create_vector_index(
        #     self.__gateway.driver,
        #     f"idx-{self.__trajectory_node_name}-{self.__trajectory_query_vector_field}",
        #     self.__trajectory_node_name,
        #     self.__trajectory_query_vector_field,
        # )

        return self.__session.execute_write(tx_fn, student_id, trajectory_entry)

    def increment_trajectory_query_repeat_count(
        self, trajectory_id: int, *, increment: int = 1
    ) -> models.StudentTrajectory:
        @unit_of_work()
        def tx_fn(tx: Session, trajectory_id: int) -> models.StudentTrajectory:
            query = f"""
            MATCH (t:{self.__trajectory_node_name}) WHERE id(t) = $trajectory_id
            SET t.query_repeat_count = t.query_repeat_count + $increment
            RETURN t
            """
            result = tx.run(query, trajectory_id=trajectory_id, increment=increment)
            node = result.single(strict=True)
            return models.StudentTrajectory(**node["t"])

        return self.__session.execute_write(tx_fn, trajectory_id, increment=increment)

    def delete_student(self, id: int) -> None:
        to_update = schemas.UpdateStudent(enabled=False)
        self.update_student(id, to_update=to_update)


# TODO: finish the fixes
