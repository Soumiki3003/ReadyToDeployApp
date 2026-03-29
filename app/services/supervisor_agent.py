import logging
import re
import time
from pydantic import BaseModel

from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.types import LLMMessage
from pydantic_ai import Agent

from app import models

from .user import UserService


class SupervisorResult(BaseModel):
    answer: str
    hint_text: str | None = None
    hint_reason: str | None = None


class SupervisorAgentService:
    RESPONSE_FALLBACK = "I couldn't find relevant information to answer your question. Please try rephrasing."

    INTENT_KEYWORDS = {
        "definition": [
            "what is",
            "what are",
            "explain",
            "define",
            "definition",
            "meaning of",
            "describe",
        ],
        "procedural": [
            "how to",
            "how do",
            "steps to",
            "implement",
            "procedure",
            "how can i",
            "what steps",
        ],
        "troubleshooting": [
            "error in",
            "not working",
            "fix",
            "bug",
            "issue",
            "broken",
            "fails",
            "exception",
            "debug",
        ],
        "example_request": [
            "example of",
            "show me",
            "example",
            "sample",
            "demo",
            "give me an example",
        ],
    }

    def __init__(
        self,
        *,
        user_service: UserService,
        graph_rag: GraphRAG,
        hint_agent: Agent,
        rewrite_agent: Agent | None = None,
        top_k: int = 5,
        similarity_threshold: float = 0.85,
        hint_by_similarity_threshold: int = 2,
        hint_procedural_history_limit: int = 3,
        confidence_threshold: float = 0.6,
        procedural_keywords: list[str] = [
            "run",
            "fix",
            "load",
            "execute",
            "implement",
            "solve",
            "compile",
            "test",
            "error",
            "code",
        ],
    ):
        self.__user_service = user_service
        self.__graph_rag = graph_rag
        self.__hint_agent = hint_agent
        self.__rewrite_agent = rewrite_agent
        self.__top_k = top_k
        self.__similarity_threshold = similarity_threshold
        self.__hint_by_similarity_threshold = hint_by_similarity_threshold
        self.__hint_procedural_history_limit = hint_procedural_history_limit
        self.__procedural_keywords = procedural_keywords
        self.__confidence_threshold = confidence_threshold
        self.__logger = logging.getLogger(__name__)

    def __retrieve_node_metadata(
        self,
        query: str,
        message_history: list[LLMMessage] | None = None,
    ):
        start_time = time.time()
        result = self.__graph_rag.search(
            query,
            message_history=message_history,
            retriever_config={"top_k": self.__top_k},
            return_context=True,
            response_fallback=self.RESPONSE_FALLBACK,
        )
        response_time_sec = round(time.time() - start_time, 2)
        self.__logger.info(f"Context retrieved in {response_time_sec} seconds")

        self.__logger.info("Parsing retriever results for node metadata...")
        retrieved_nodes, scores = [], []
        if retriever_result := result.retriever_result:
            try:
                for item in retriever_result.items:
                    node_name = "Unknown"
                    if isinstance(item.content, str):
                        match = re.search(r"'name': '([^']+)'", item.content)
                        if match:
                            node_name = match.group(1)
                    retrieved_nodes.append(node_name)
                    if isinstance(item.metadata, dict):
                        scores.append(item.metadata.get("score"))
            except Exception as e:
                self.__logger.warning(f"Failed to parse retriever result metadata: {e}")

        self.__logger.info(f"Retrieved nodes: {len(retrieved_nodes)}")
        return result, retrieved_nodes, scores, response_time_sec

    def __classify_intent(self, query: str) -> str:
        """Classify student query intent into categories.

        Returns one of: definition, procedural, troubleshooting, example_request, or context_request.
        """
        q_lower = query.lower().strip()
        for intent, keywords in self.INTENT_KEYWORDS.items():
            if any(kw in q_lower for kw in keywords):
                return intent
        return "context_request"

    def __get_interaction_type(self, query: str):
        q_lower = query.lower()
        keywords_mapping = {
            "hint_request": ["hint", "help", "assist", "clue", "suggest"],
            "code_request": ["code", "script", "function", "write", "implement"],
            "concept_request": [
                "concept",
                "explain",
                "definition",
                "understand",
                "what is",
            ],
        }

        for interaction_type, keywords in keywords_mapping.items():
            if any(word in q_lower for word in keywords):
                return interaction_type
        return "context_request"

    def __get_similar_trajectory_queries(self, query: str, *, user_id: str):
        trajectories: list[str] = []

        # TODO: Why not only use the query_similarity as a exact match would be always present in the list?
        for item in self.__user_service.get_user_trajectory_by_query_exact_match(
            user_id, query
        ):
            if item.id and item.id not in trajectories:
                trajectories.append(item.id)

        for item in self.__user_service.get_user_trajectory_by_query_similarity(
            user_id, query, threshold=self.__similarity_threshold
        ):
            if item.id and item.id not in trajectories:
                trajectories.append(item.id)

        return list(trajectories)

    def __generate_hint(
        self,
        query: str,
        query_repeat_count: int,
        *,
        retrieved_nodes: list[str],
        user_id: str,
    ):
        hint_triggered = query_repeat_count >= self.__hint_by_similarity_threshold
        hint_reason = None
        hint_text = None

        if hint_triggered:
            hint_reason = "Repeated query (possible confusion)"
            hint_prompt = (
                f"Provide a short, encouraging hint to help the student progress on: '{query}'. "
                f"Focus on conceptual reinforcement rather than giving the answer directly. "
                f"Context nodes: {retrieved_nodes[:3]}"
            )
            hint_text = self.__hint_agent.run_sync(hint_prompt).output.strip()
            self.__logger.info(f"Hint triggered: {hint_reason} -> {hint_text}")
        else:
            last_trajectories = self.__user_service.get_user_trajectory(
                user_id, limit=self.__hint_procedural_history_limit
            )
            recent_queries = [item.query.lower() for item in last_trajectories]
            recent_queries.append(query.lower())

            def is_procedural(q):
                return any(k in q for k in self.__procedural_keywords)

            if all(is_procedural(q) for q in recent_queries + [query.lower()]):
                hint_triggered = True
                hint_reason = "Procedural impasse (stuck on how-to steps)"
                hint_prompt = (
                    f"The student has been asking several procedural questions in a row. "
                    f"Generate a reflective, conceptual hint encouraging them to focus on the underlying idea of '{query}'. "
                    f"Do not reveal exact code; instead, suggest understanding the concept that supports this step."
                )
                hint_text = self.__hint_agent.run_sync(hint_prompt).output.strip()
                self.__logger.info(f"Hint triggered: {hint_reason} -> {hint_text}")

        return hint_triggered, hint_reason, hint_text

    def __rewrite_response(self, raw_answer: str, query: str) -> str:
        if not self.__rewrite_agent or not raw_answer:
            return raw_answer

        prompt = (
            "Rewrite the following answer for a student. "
            "Remove any references to internal system structures: "
            "knowledge graph nodes, concept graph, retrieved nodes, "
            "graph structure, PREREQUISITE_FOR relationships, "
            "or any other internal metadata. "
            "Make the answer natural, educational, and self-contained. "
            "\n\nStudent question: " + query + "\n\nRaw answer: " + raw_answer
        )
        result = self.__rewrite_agent.run_sync(prompt)
        return result.output.strip()

    def retrieve_context(
        self,
        user_id: str,
        query: str,
        course_id: str,
        message_history: list[LLMMessage] | None = None,
    ):
        try:
            self.__logger.info(f"Loading user {user_id} state...")
            user = self.__user_service.get_user(user_id)
            if not user:
                self.__logger.warning(f"User {user_id} not found!")
                return None
            if not user.id:
                self.__logger.warning(f"User {user_id} has no ID!")
                return None

            self.__logger.info("Retrieving node metadata...")
            rag_result, retrieved_nodes, scores, response_time_sec = (
                self.__retrieve_node_metadata(query, message_history)
            )
            node_entry_count = len(retrieved_nodes)

            # Check confidence threshold
            if (
                scores
                and scores[0] is not None
                and scores[0] < self.__confidence_threshold
            ):
                self.__logger.warning(
                    f"Low confidence query (score={scores[0]:.2f} < {self.__confidence_threshold:.2f}): {query}"
                )
                return SupervisorResult(
                    answer=self.RESPONSE_FALLBACK,
                    hint_text=None,
                    hint_reason=None,
                )

            self.__logger.info("Determining interaction type...")
            interaction_type = self.__classify_intent(query)

            self.__logger.info("Computing node count and repeat count...")
            similar_trajectory_ids = self.__get_similar_trajectory_queries(
                query, user_id=user.id
            )
            query_repeat_count = len(similar_trajectory_ids)

            hint_triggered, hint_reason, hint_text = self.__generate_hint(
                query,
                query_repeat_count,
                retrieved_nodes=retrieved_nodes,
                user_id=user.id,
            )

            raw_answer = rag_result.answer if rag_result else ""
            rewritten_answer = self.__rewrite_response(raw_answer, query)

            new_trajectory = models.UserTrajectory(
                user_id=user.id,
                query=query,
                retrieved_nodes=retrieved_nodes,
                scores=scores,
                interaction_type=interaction_type,
                query_repeat_count=query_repeat_count + 1,
                node_entry_count=node_entry_count,
                response_time_sec=response_time_sec,
                hint_triggered=hint_triggered,
                hint_reason=hint_reason,
                hint_text=hint_text,
                raw_answer=raw_answer,
                course_id=course_id,
            )
            self.__user_service.add_trajectory_entry(user_id, new_trajectory)
            self.__logger.info(
                f"Context retrieval logged. ({interaction_type}, {node_entry_count} nodes, {response_time_sec}s)"
            )
            return SupervisorResult(
                answer=rewritten_answer,
                hint_text=hint_text,
                hint_reason=hint_reason,
            )

        except Exception as e:
            self.__logger.error(f"Error occurred while retrieving context: {e}")
            return None
