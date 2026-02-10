import logging
import re
import time

from app import models
from app.models import student
from app.utils import hash_string
from .student import StudentService, StudentTrajectoryService
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.retrievers import VectorRetriever

logger = logging.getLogger(__name__)

GraphRAG.search()


class SupervisorAgentService:
    def __init__(
        self,
        *,
        student_service: StudentService,
        trajectory_service: StudentTrajectoryService,
        graph_rag: GraphRAG,
        top_k: int = 5,
        similarity_threshold: float = 0.85,
    ):
        self.__student_service = student_service
        self.__trajectory_service = trajectory_service
        self.__graph_rag = graph_rag
        self.__top_k = top_k
        self.__similarity_threshold = similarity_threshold

    def __retrieve_node_metadata(self, query: str):
        start_time = time.time()
        result = self.__graph_rag.search(
            query,
            retriever_config={"top_k": self.__top_k},
            return_context=True,
        )
        response_time = round(time.time() - start_time, 2)
        logger.info(f"Context retrieved in {response_time} seconds")

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
        return retrieved_nodes, scores

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

    def __compute_node_count_and_repeat_count(
        self,
        student: models.Student,
        query: str
    ):
        exact_matches_ids = [item.id for item in self.__trajectory_service.get_by_query(student.id, query)]
        pending_items = [item for item in student.trajectories if item.id not in exact_matches]


        for item in student.trajectory:
            if items := self.__trajectory_service.get_by_query(
                item.student_id,
                query,
                exclude_ids=[item.id],
                limit=None,
                offset=None,
            ):
                
            try:
                result = self.__graph_rag.retriever.search(
                    query_text="", retriever_config={"top_k": 1}
                )
            except Exception as e:
                logger.warning(
                    f"Vector retriever search failed during repeat count computation: {e}"
                )
            else:
                pass

    def retrieve_context(self, student_id: int, query: str, *, top_k: int = 5):
        # TODO: implement supervisor_agent.py

        student = self.__student_service.get_student(student_id)
        if not student:
            return None

        retrieved_nodes, scores = self.__retrieve_node_metadata(query)
        interaction_type = self.__get_interaction_type(query)
