import logging
import re
import time

from neo4j_graphrag.generation import GraphRAG
from pydantic_ai import Agent

from app import models
from app.utils import hash_string

from .student import StudentService

logger = logging.getLogger(__name__)


class SupervisorAgentService:
    def __init__(
        self,
        *,
        student_service: StudentService,
        graph_rag: GraphRAG,
        hint_agent: Agent,
        top_k: int = 5,
        similarity_threshold: float = 0.85,
        hint_by_similarity_threshold: int = 2,
        hint_procedural_history_limit: int = 3,
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
        self.__student_service = student_service
        self.__graph_rag = graph_rag
        self.__hint_agent = hint_agent
        self.__top_k = top_k
        self.__similarity_threshold = similarity_threshold
        self.__hint_by_similarity_threshold = hint_by_similarity_threshold
        self.__hint_procedural_history_limit = hint_procedural_history_limit
        self.__procedural_keywords = procedural_keywords

    def __retrieve_node_metadata(self, query: str):
        start_time = time.time()
        result = self.__graph_rag.search(
            query,
            retriever_config={"top_k": self.__top_k},
            return_context=True,
        )
        response_time_sec = round(time.time() - start_time, 2)
        logger.info(f"Context retrieved in {response_time_sec} seconds")

        logger.info("Parsing retriever results for node metadata...")
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
                logger.warning(f"Failed to parse retriever result metadata: {e}")

        logger.info(f"Retrieved nodes: {len(retrieved_nodes)}")
        return result, retrieved_nodes, scores, response_time_sec

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

    def __get_student_trajectory_similar_queries(self, query: str, *, student_id: str):
        trajectories: list[str] = []

        # TODO: Why not only use the query_similarity as a exact match would be always present in the list?
        for item in self.__student_service.get_student_trajectory_by_query_exact_match(
            student_id, query
        ):
            if item.id and item.id not in trajectories:
                trajectories.append(item.id)

        for item in self.__student_service.get_student_trajectory_by_query_similarity(
            student_id, query, threshold=self.__similarity_threshold
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
        student_id: str,
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
            logger.info(f"💡 Hint triggered: {hint_reason} → {hint_text}")
        else:
            last_trajectories = self.__student_service.get_student_trajectory(
                student_id, limit=self.__hint_procedural_history_limit
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
                logger.info(f"Hint triggered: {hint_reason} → {hint_text}")

        return hint_triggered, hint_reason, hint_text

    def retrieve_context(self, student_id: str, query: str):
        try:
            logger.info(f"Loading student {student_id} state...")
            student = self.__student_service.get_student(student_id)
            if not student:
                logger.warning(f"Student {student_id} not found!")
                return None
            if not student.id:
                logger.warning(f"Student {student_id} has no ID!")
                return None

            logger.info("Retrieving node metadata...")
            rag_result, retrieved_nodes, scores, response_time_sec = (
                self.__retrieve_node_metadata(query)
            )
            node_entry_count = len(retrieved_nodes)

            logger.info("Determining interaction type...")
            interaction_type = self.__get_interaction_type(query)

            logger.info("Computing node count and repeat count...")
            similar_trajectory_ids = self.__get_student_trajectory_similar_queries(
                query, student_id=student.id
            )
            query_repeat_count = len(similar_trajectory_ids)

            hint_triggered, hint_reason, hint_text = self.__generate_hint(
                query,
                query_repeat_count,
                retrieved_nodes=retrieved_nodes,
                student_id=student.id,
            )

            new_trajectory = models.StudentTrajectory(
                student_id=student.id,
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
            )
            self.__student_service.add_trajectory_entry(student_id, new_trajectory)
            logger.info(
                f"✅ Context retrieval logged. ({interaction_type}, {node_entry_count} nodes, {response_time_sec}s)"
            )
            return rag_result

        except Exception as e:
            logger.error(f"Error occurred while retrieving context: {e}")
            return None
