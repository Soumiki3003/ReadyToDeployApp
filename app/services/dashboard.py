import logging
from collections import defaultdict
from contextlib import AbstractContextManager
from typing import Any, Callable

from neo4j import ManagedTransaction, Session, unit_of_work

from app.models.user import UserTrajectory


class DashboardService:
    __user_node_name = "User"
    __trajectory_node_name = "UserTrajectory"
    __trajectory_rel_name = "HAS_TRAJECTORY"

    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]],
    ):
        self.__session_factory = session_factory
        self.__logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Struggle formula
    # ------------------------------------------------------------------

    @staticmethod
    def _struggle(entry: UserTrajectory) -> float:
        """Calculate the struggle score for a single trajectory entry.

        ``struggle = (query_repeat_count * 2)
                    + (3 if hint_triggered else 0)
                    + min(response_time_sec / 10, 3)``
        """
        repeat_component = entry.query_repeat_count * 2
        hint_component = 3.0 if entry.hint_triggered else 0.0
        time_component = min(entry.response_time_sec / 10.0, 3.0)
        return repeat_component + hint_component + time_component

    # ------------------------------------------------------------------
    # Internal query helper
    # ------------------------------------------------------------------

    def _fetch_trajectories(self, course_id: str) -> list[UserTrajectory]:
        """Query all UserTrajectory entries for a given course."""

        @unit_of_work()
        def tx_fn(
            tx: ManagedTransaction, course_id: str
        ) -> list[UserTrajectory]:
            query = f"""
            MATCH (u:{self.__user_node_name})
                  -[:{self.__trajectory_rel_name}]->
                  (t:{self.__trajectory_node_name})
            WHERE t.course_id = $course_id
            RETURN t, u.id AS user_id
            ORDER BY t.timestamp ASC
            """
            result = tx.run(query, course_id=course_id)
            trajectories: list[UserTrajectory] = []
            for record in result:
                data = dict(record["t"])
                data["user_id"] = record["user_id"]
                trajectories.append(UserTrajectory(**data))
            return trajectories

        with self.__session_factory() as session:
            return session.execute_read(tx_fn, course_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_node_struggle(self, course_id: str) -> list[dict]:
        """Return per-node struggle scores (0-9 scale conceptually).

        Each entry: ``{"node_id": str, "struggle": float}``
        Struggle is summed across all students for each node.
        """
        trajectories = self._fetch_trajectories(course_id)
        node_scores: dict[str, float] = defaultdict(float)

        for entry in trajectories:
            score = self._struggle(entry)
            for node_id in entry.retrieved_nodes:
                node_scores[node_id] += score

        return [
            {"node_id": nid, "struggle": s} for nid, s in node_scores.items()
        ]

    def calculate_student_struggle(self, course_id: str) -> list[dict]:
        """Return per-student struggle scores (6-16 scale conceptually).

        Each entry: ``{"student_id": str, "struggle": float}``
        Struggle is summed across all trajectory entries for each student.
        """
        trajectories = self._fetch_trajectories(course_id)
        student_scores: dict[str, float] = defaultdict(float)

        for entry in trajectories:
            student_scores[entry.user_id] += self._struggle(entry)

        return [
            {"student_id": uid, "struggle": s}
            for uid, s in student_scores.items()
        ]
