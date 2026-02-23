from contextlib import AbstractContextManager
import logging
from typing import Any, Callable, Literal

from neo4j import ManagedTransaction, Session, unit_of_work
from neo4j_graphrag.generation import GraphRAG
from pydantic_ai import Embedder

from app import models, schemas
from app.utils import hash_string

from .auth import AuthService


class UserService:
    __user_node_name = "User"

    __trajectory_node_name = "UserTrajectory"
    __trajectory_rel_name = "HAS_TRAJECTORY"
    __trajectory_prev_rel_name = "PREVIOUS_TRAJECTORY"

    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]],
        embedder: Embedder,
        rag: GraphRAG,
        auth_service: AuthService,
        trajectory_vector_index_field: str,
        trajectory_full_text_index_field: str,
    ):
        self.__session_factory = session_factory
        self.__embedder = embedder
        self.__auth_service = auth_service
        self.__rag = rag
        self.__trajectory_vector_index_field = trajectory_vector_index_field
        self.__trajectory_full_text_index_field = trajectory_full_text_index_field
        self.__logger = logging.getLogger(__name__)

    def create_user(self, item: schemas.CreateUser) -> models.User:
        @unit_of_work()
        def tx_fn(tx: ManagedTransaction, user: models.User) -> models.User:
            query = f"CREATE (u:{self.__user_node_name} $props) RETURN u"

            self.__logger.debug(f"Executing user creation query for {user.email}")
            result = tx.run(
                query,
                props=user.model_dump(by_alias=True),
            )
            node = result.single(strict=True)
            self.__logger.debug("User node created in Neo4j")
            return models.User(**node["u"])

        self.__logger.info(f"Creating new user with email: {item.email}")
        self.__logger.debug(f"Checking if user with email {item.email} already exists")
        user_by_email = self.get_user_by_email(item.email)
        if user_by_email:
            self.__logger.warning(
                f"User creation failed: email {item.email} already exists"
            )
            raise ValueError(f"User with email {item.email} already exists")

        self.__logger.debug("Hashing user password")
        password_hash = self.__auth_service.hash_password(item.password)

        # Create User model with auto-generated ID
        new_user = models.User(
            name=item.name,
            email=item.email,
            password=password_hash,
            role=item.role,
            enabled=item.enabled,
        )

        with self.__session_factory() as session:
            new_user = session.execute_write(tx_fn, new_user)
        self.__logger.info(f"User created successfully: {item.email}")
        return new_user

    def get_user(self, id: str) -> models.User | None:
        @unit_of_work()
        def tx_fn(tx: ManagedTransaction, id: str) -> models.User | None:
            query = f"MATCH (u:{self.__user_node_name}) WHERE u.id = $id RETURN u"
            result = tx.run(query, id=id)
            record = result.single()
            if record:
                return models.User(**record["u"])
            return None

        with self.__session_factory() as session:
            user = session.execute_read(tx_fn, id)
        return user

    def get_user_by_email(self, email: str) -> models.User | None:
        @unit_of_work()
        def tx_fn(tx: ManagedTransaction, email: str) -> models.User | None:
            query = f"MATCH (u:{self.__user_node_name}) WHERE u.email = $email RETURN u"
            result = tx.run(query, email=email)
            record = result.single()
            if record:
                return models.User(**record["u"])
            return None

        with self.__session_factory() as session:
            user = session.execute_read(tx_fn, email)
        return user

    def authenticate(self, email: str, password: str) -> models.User | None:
        self.__logger.debug(f"Authenticating user: {email}")
        user = self.get_user_by_email(email)
        if not user:
            self.__logger.debug(f"User not found: {email}")
            return None
        if not self.__auth_service.verify_password(password, user.password):
            self.__logger.debug(f"Invalid password for user: {email}")
            return None
        self.__logger.info(f"User authenticated successfully: {email}")
        return user

    def update_user(
        self,
        id: str,
        *,
        to_update: schemas.UpdateUser,
    ) -> models.User:
        @unit_of_work()
        def tx_fn(
            tx: ManagedTransaction, id: str, to_update: schemas.UpdateUser
        ) -> models.User:
            params = to_update.model_dump(exclude_unset=True, by_alias=True)
            query = f"""
            MATCH (u:{self.__user_node_name}) WHERE u.id = $id
            SET u += $props
            RETURN u
            """
            result = tx.run(query, id=id, props=params)
            node = result.single(strict=True)
            return models.User(**node["u"])

        with self.__session_factory() as session:
            return session.execute_write(tx_fn, id, to_update)

    def get_user_trajectory(
        self,
        user_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
        timestamp_order: Literal["ASC", "DESC"] = "DESC",
    ) -> list[models.UserTrajectory]:
        @unit_of_work()
        def tx_fn(
            tx: ManagedTransaction,
            user_id: str,
            *,
            limit: int | None = None,
            offset: int | None = None,
            timestamp_order: Literal["ASC", "DESC"] = "DESC",
        ) -> list[models.UserTrajectory]:
            if limit is not None and limit <= 0:
                raise ValueError("Limit must be a positive integer")
            if offset is not None and offset < 0:
                raise ValueError("Offset must be a non-negative integer")

            query = f"""
            MATCH (u:{self.__user_node_name})-[:{self.__trajectory_rel_name}]->(t:{self.__trajectory_node_name})
            WHERE u.id = $user_id
            """
            params: dict[str, Any] = {}
            if limit is not None:
                query += " LIMIT $limit"
                params["limit"] = limit
            if offset is not None:
                query += " SKIP $offset"
                params["offset"] = offset
            query += (
                f" RETURN t, u.id AS user_id ORDER BY t.timestamp {timestamp_order}"
            )

            result = tx.run(
                query,
                params,
                user_id=user_id,
            )
            trajectories = []
            for record in result:
                data = dict(record["t"])
                data["user_id"] = record["user_id"]
                trajectories.append(models.UserTrajectory(**data))
            return trajectories

        with self.__session_factory() as session:
            return session.execute_read(
                tx_fn,
                user_id,
                limit=limit,
                offset=offset,
                timestamp_order=timestamp_order,
            )

    def get_user_trajectory_by_query_exact_match(
        self,
        user_id: str,
        query: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[models.UserTrajectory]:
        @unit_of_work()
        def tx_fn(
            tx: ManagedTransaction,
            user_id: str,
            query: str,
            limit: int | None = None,
            offset: int | None = None,
        ) -> list[models.UserTrajectory]:

            statement = f"""
            MATCH (u:{self.__user_node_name})-[:{self.__trajectory_rel_name}]->(t:{self.__trajectory_node_name})
            WHERE u.id = $user_id AND t.{self.__trajectory_full_text_index_field} = $query_hash
            """

            parameters = {}
            if limit is not None:
                statement += " LIMIT $limit"
                parameters["limit"] = limit
            if offset is not None:
                statement += " SKIP $offset"
                parameters["offset"] = offset
            statement += " RETURN t, u.id AS user_id ORDER BY t.timestamp DESC"

            result = tx.run(
                statement,
                parameters,
                user_id=user_id,
                query_hash=hash_string(query),
            )
            trajectories = []
            for record in result:
                data = dict(record["t"])
                data["user_id"] = record["user_id"]
                trajectories.append(models.UserTrajectory(**data))
            return trajectories

        with self.__session_factory() as session:
            return session.execute_read(
                tx_fn, user_id, query, limit=limit, offset=offset
            )

    def get_user_trajectory_by_query_similarity(
        self,
        user_id: str,
        query: str,
        *,
        threshold: float | None = None,
        limit: int | None = None,
    ) -> list[models.UserTrajectory]:
        config = {}
        if limit is not None:
            config["top_k"] = limit
        if threshold is not None:
            config["similarity_threshold"] = threshold
        try:
            result = self.__rag.retriever.get_search_results(
                query_text=query,
                retriever_config=config,
                filters={"user_id": user_id},
            )
            return [models.UserTrajectory(**item.data()) for item in result.records]
        except Exception as e:
            self.__logger.warning(
                f"Vector retriever search failed during similarity retrieval: {e}"
            )
            return []

    def add_trajectory_entry(
        self,
        user_id: str,
        trajectory_entry: models.UserTrajectory,
    ) -> models.UserTrajectory:
        self.__logger.info(f"Adding trajectory entry for user {user_id}")
        self.__logger.debug(f"Query: {trajectory_entry.query[:100]}...")

        @unit_of_work()
        def tx_fn(
            tx: ManagedTransaction,
            user_id: str,
            trajectory_entry: models.UserTrajectory,
        ) -> models.UserTrajectory:
            query = f"""
            MATCH (u:{self.__user_node_name}) WHERE u.id = $user_id
            CREATE (t:{self.__trajectory_node_name} $props)
            CREATE (u)-[rel:{self.__trajectory_rel_name}]->(t)
            WITH u, t, rel
            OPTIONAL MATCH (u)-[prev_rel:{self.__trajectory_rel_name}]->(prev_t:{self.__trajectory_node_name})
            WHERE prev_t <> t
            ORDER BY prev_t.timestamp DESC
            LIMIT 1
            CREATE (t)-[:{self.__trajectory_prev_rel_name}]->(prev_t)
            RETURN t, u.id AS user_id
            """

            params = trajectory_entry.model_dump(by_alias=True)
            self.__logger.debug("Hashing query for full-text index")
            params[self.__trajectory_full_text_index_field] = hash_string(
                trajectory_entry.query
            )
            self.__logger.debug("Embedding query for vector search")
            params[self.__trajectory_vector_index_field] = (
                self.__embedder.embed_documents_sync([trajectory_entry.query])[0]
            )

            self.__logger.debug("Creating trajectory node in Neo4j")
            result = tx.run(
                query,
                params,
                user_id=user_id,
            )
            node = result.single(strict=True)
            data = dict(node["t"])
            data["user_id"] = node["user_id"]
            self.__logger.debug("Trajectory node created successfully")
            return models.UserTrajectory(**data)

        with self.__session_factory() as session:
            result = session.execute_write(tx_fn, user_id, trajectory_entry)
        self.__logger.info(f"Trajectory entry added successfully for user {user_id}")
        return result

    def increment_trajectory_query_repeat_count(
        self, trajectory_id: str, *, increment: int = 1
    ) -> models.UserTrajectory:
        self.__logger.debug(
            f"Incrementing query repeat count for trajectory {trajectory_id} by {increment}"
        )

        @unit_of_work()
        def tx_fn(
            tx: ManagedTransaction,
            trajectory_id: str,
            increment: int,
        ) -> models.UserTrajectory:
            query = f"""
            MATCH (t:{self.__trajectory_node_name}) WHERE id(t) = $trajectory_id
            SET t.query_repeat_count = t.query_repeat_count + $increment
            RETURN t
            """
            result = tx.run(
                query,
                trajectory_id=trajectory_id,
                increment=increment,
            )
            node = result.single(strict=True)
            return models.UserTrajectory(**node["t"])

        with self.__session_factory() as session:
            return session.execute_write(tx_fn, trajectory_id, increment)

    def get_users_by_role(self, role: str) -> list[models.User]:
        @unit_of_work()
        def tx_fn(tx: ManagedTransaction, role: str) -> list[models.User]:
            query = (
                f"MATCH (u:{self.__user_node_name}) "
                "WHERE u.role = $role AND u.enabled = true "
                "RETURN u ORDER BY u.name"
            )
            result = tx.run(query, role=role)
            return [models.User(**record["u"]) for record in result]

        with self.__session_factory() as session:
            return session.execute_read(tx_fn, role)

    def delete_user(self, id: str) -> None:
        to_update = schemas.UpdateUser(enabled=False)
        self.update_user(id, to_update=to_update)
