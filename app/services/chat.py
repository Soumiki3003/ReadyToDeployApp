import logging
from contextlib import AbstractContextManager
from typing import Any, Callable

from neo4j import ManagedTransaction, Session, unit_of_work
from neo4j_graphrag.types import LLMMessage

from app import models


class ChatService:
    __message_node_name = "ChatMessage"
    __user_node_name = "User"
    __course_node_label = models.KnowledgeType.ROOT.value
    __user_rel_name = "HAS_CHAT_MESSAGE"
    __course_rel_name = "HAS_CHAT_MESSAGE"

    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]],
    ):
        self.__session_factory = session_factory
        self.__logger = logging.getLogger(__name__)

    def get_messages(
        self,
        user_id: str,
        course_id: str,
        *,
        limit: int | None = None,
    ) -> list[models.ChatMessage]:
        @unit_of_work()
        def tx_fn(
            tx: ManagedTransaction,
            user_id: str,
            course_id: str,
            limit: int | None,
        ) -> list[models.ChatMessage]:
            query = f"""
            MATCH (u:{self.__user_node_name})-[:{self.__user_rel_name}]->(m:{self.__message_node_name})<-[:{self.__course_rel_name}]-(c:{self.__course_node_label})
            WHERE u.id = $user_id AND c.id = $course_id
            RETURN m ORDER BY m.timestamp ASC
            """
            params: dict[str, Any] = {}
            if limit is not None:
                query = f"""
                MATCH (u:{self.__user_node_name})-[:{self.__user_rel_name}]->(m:{self.__message_node_name})<-[:{self.__course_rel_name}]-(c:{self.__course_node_label})
                WHERE u.id = $user_id AND c.id = $course_id
                WITH m ORDER BY m.timestamp DESC
                LIMIT $limit
                RETURN m ORDER BY m.timestamp ASC
                """
                params["limit"] = limit

            result = tx.run(query, params, user_id=user_id, course_id=course_id)
            return [models.ChatMessage(**record["m"]) for record in result]

        with self.__session_factory() as session:
            return session.execute_read(tx_fn, user_id, course_id, limit)

    def add_message(
        self,
        user_id: str,
        course_id: str,
        message: models.ChatMessage,
    ) -> models.ChatMessage:
        self.__logger.debug(
            f"Adding {message.role} chat message for user {user_id} in course {course_id}"
        )

        @unit_of_work()
        def tx_fn(
            tx: ManagedTransaction,
            user_id: str,
            course_id: str,
            message: models.ChatMessage,
        ) -> models.ChatMessage:
            query = f"""
            MATCH (u:{self.__user_node_name}) WHERE u.id = $user_id
            MATCH (c:{self.__course_node_label}) WHERE c.id = $course_id
            CREATE (m:{self.__message_node_name} $props)
            CREATE (u)-[:{self.__user_rel_name}]->(m)
            CREATE (c)-[:{self.__course_rel_name}]->(m)
            RETURN m
            """
            result = tx.run(
                query,
                user_id=user_id,
                course_id=course_id,
                props=message.model_dump(mode="json", by_alias=True),
            )
            node = result.single(strict=True)
            return models.ChatMessage(**node["m"])

        with self.__session_factory() as session:
            return session.execute_write(tx_fn, user_id, course_id, message)

    @staticmethod
    def to_llm_messages(messages: list[models.ChatMessage]) -> list[LLMMessage]:
        return [
            LLMMessage(role=msg.role.value, content=msg.content) for msg in messages
        ]
