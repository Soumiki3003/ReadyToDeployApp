import logging
import re
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
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_conceptual_ancestor(self, course_id: str, node_name: str) -> dict | None:
        """Given any KG node name (C05, P05, P05-step1, etc.) return its conceptual ancestor dict."""

        @unit_of_work()
        def tx_fn(tx: ManagedTransaction, course_id: str, node_name: str) -> dict | None:
            result = tx.run(
                """
                MATCH (root {id: $course_id, type: 'root'})-[:HAS_CHILD*1..5]->(n)
                WHERE n.name = $node_name
                WITH n
                MATCH path = (root2 {type: 'root'})-[:HAS_CHILD*1..2]->(c {type: 'conceptual'})-[:HAS_CHILD*0..3]->(n)
                RETURN c.name AS name, c.label AS label, c.id AS id
                LIMIT 1
                """,
                course_id=course_id,
                node_name=node_name,
            )
            row = result.single()
            return dict(row) if row else None

        with self.__session_factory() as session:
            return session.execute_read(tx_fn, course_id, node_name)

    def _fetch_conceptual_nodes(self, course_id: str) -> list[dict]:
        """Return all conceptual nodes for a course as {id, name, label, keywords}."""

        @unit_of_work()
        def tx_fn(tx: ManagedTransaction, course_id: str) -> list[dict]:
            result = tx.run(
                """
                MATCH (root {id: $course_id, type: 'root'})-[:HAS_CHILD*1..2]->(n {type: 'conceptual'})
                RETURN n.id AS id, n.name AS name, n.label AS label,
                       n.definition AS definition, n.learning_objective AS learning_objective
                """,
                course_id=course_id,
            )
            return [dict(r) for r in result]

        with self.__session_factory() as session:
            return session.execute_read(tx_fn, course_id)

    _STOP_WORDS = {
        "the", "a", "an", "and", "or", "for", "to", "of", "in", "is", "are",
        "with", "how", "what", "does", "do", "i", "me", "my", "can", "you",
        "just", "about", "explain", "give", "show", "tell", "please", "still",
        "confused", "know", "it", "this", "that", "why", "when", "where",
        "actually", "really", "concrete", "steps", "dont", "not",
    }

    @staticmethod
    def _stem(word: str) -> str:
        for suffix in ("ing", "tion", "ment", "ness", "ful", "less", "ed", "er", "ly", "es", "s"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                return word[: -len(suffix)]
        return word

    @classmethod
    def _tokenize(cls, text: str) -> set[str]:
        words = re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).split()
        return {cls._stem(w) for w in words if w not in cls._STOP_WORDS and len(w) > 2}

    def _match_conceptual_node(
        self,
        query: str,
        conceptual_nodes: list[dict],
        retrieved_nodes: list[str] | None = None,
    ) -> dict | None:
        """Return the best-matching conceptual node.

        Uses retrieved_nodes (RAG output) as primary signal — more accurate than
        query-text matching because the RAG already resolved the right KG nodes.
        Falls back to stemmed query-keyword overlap when retrieved_nodes is empty.
        """
        if not conceptual_nodes:
            return None

        def _score_against(tokens: set[str], node: dict) -> int:
            node_text = " ".join(filter(None, [
                node.get("name", ""),
                node.get("definition", ""),
                node.get("learning_objective", ""),
            ]))
            return len(tokens & self._tokenize(node_text))

        # Primary: retrieved_nodes may contain direct KG node IDs (C05, P05, P05-step1)
        # These come from ContentChunk.kg_node_id — exact match, most reliable
        if retrieved_nodes:
            conceptual_ids = {n["name"] for n in conceptual_nodes}
            for rn in retrieved_nodes:
                # Direct conceptual node match (e.g. "C05")
                if rn in conceptual_ids:
                    return next(n for n in conceptual_nodes if n["name"] == rn)
                # Procedural/step node — find conceptual ancestor by prefix (P05→C05, P05-step1→C05)
                # Convention: Pxx nodes belong to Cxx (same number suffix)
                if rn.startswith("P") or "-step" in rn:
                    base = rn.split("-")[0]  # "P05-step1" → "P05"
                    concept_id = "C" + base[1:]  # "P05" → "C05"
                    match = next((n for n in conceptual_nodes if n["name"] == concept_id), None)
                    if match:
                        return match
                # Assessment node (A05 → C05)
                if rn.startswith("A"):
                    concept_id = "C" + rn[1:].split("-")[0]
                    match = next((n for n in conceptual_nodes if n["name"] == concept_id), None)
                    if match:
                        return match

            # Fallback within retrieved_nodes: keyword overlap
            scores: dict[str, int] = {n.get("name", ""): 0 for n in conceptual_nodes}
            for rn in retrieved_nodes:
                rn_tokens = self._tokenize(rn)
                if not rn_tokens:
                    continue
                for node in conceptual_nodes:
                    s = _score_against(rn_tokens, node)
                    scores[node["name"]] = scores.get(node["name"], 0) + s
            best = max(conceptual_nodes, key=lambda n: scores.get(n["name"], 0))
            if scores.get(best["name"], 0) > 0:
                return best

        # Fallback: stemmed query-keyword overlap
        query_tokens = self._tokenize(query)
        best_node, best_score = None, 0
        for node in conceptual_nodes:
            s = _score_against(query_tokens, node)
            if s > best_score:
                best_score = s
                best_node = node
        return best_node if best_node and best_score > 0 else None

    def _fetch_procedural_nodes_for_concept(self, course_id: str, concept_name: str) -> list[dict]:
        """Return procedural nodes that are children of the given conceptual node."""

        @unit_of_work()
        def tx_fn(tx: ManagedTransaction, course_id: str, concept_name: str) -> list[dict]:
            result = tx.run(
                """
                MATCH (root {id: $course_id, type: 'root'})-[:HAS_CHILD*1..2]->(c {type: 'conceptual', name: $concept_name})
                -[:HAS_CHILD]->(p {type: 'procedural'})
                RETURN p.name AS name, p.label AS label
                ORDER BY p.percent_done ASC
                """,
                course_id=course_id,
                concept_name=concept_name,
            )
            return [dict(r) for r in result]

        with self.__session_factory() as session:
            return session.execute_read(tx_fn, course_id, concept_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_node_engagement(self, course_id: str) -> list[dict]:
        """Return per-conceptual-node question counts across all students.

        Each entry: ``{"node_id": str, "node_name": str, "question_count": int,
                        "students": list[str], "hint_count": int}``
        """
        trajectories = self._fetch_trajectories(course_id)
        conceptual_nodes = self._fetch_conceptual_nodes(course_id)
        node_counts: dict[str, dict] = {}

        for entry in trajectories:
            node = self._match_conceptual_node(entry.query, conceptual_nodes, entry.retrieved_nodes)
            node_id = node["name"] if node else "unknown"
            node_label = node.get("label") or node_id if node else "Unknown"
            if node_id not in node_counts:
                node_counts[node_id] = {
                    "node_id": node_id,
                    "node_name": node_label,
                    "question_count": 0,
                    "hint_count": 0,
                    "students": set(),
                }
            node_counts[node_id]["question_count"] += 1
            node_counts[node_id]["students"].add(entry.user_id)
            if entry.hint_triggered:
                node_counts[node_id]["hint_count"] += 1

        return [
            {
                "node_id": v["node_id"],
                "node_name": v["node_name"],
                "question_count": v["question_count"],
                "hint_count": v["hint_count"],
                "student_count": len(v["students"]),
            }
            for v in sorted(node_counts.values(), key=lambda x: x["question_count"], reverse=True)
        ]

    def calculate_student_activity(self, course_id: str) -> list[dict]:
        """Return per-student activity summary.

        Each entry: ``{"student_id": str, "total_questions": int,
                        "hints_triggered": int, "unique_topics": int}``
        """
        trajectories = self._fetch_trajectories(course_id)
        conceptual_nodes = self._fetch_conceptual_nodes(course_id)
        student_data: dict[str, dict] = {}

        for entry in trajectories:
            uid = entry.user_id
            if uid not in student_data:
                student_data[uid] = {
                    "student_id": uid,
                    "total_questions": 0,
                    "hints_triggered": 0,
                    "topics": set(),
                    "questions": [],
                }
            student_data[uid]["total_questions"] += 1
            if entry.hint_triggered:
                student_data[uid]["hints_triggered"] += 1
            node = self._match_conceptual_node(entry.query, conceptual_nodes, entry.retrieved_nodes)
            node_label = node.get("label") or node.get("name") if node else None
            if node_label:
                student_data[uid]["topics"].add(node_label)
            student_data[uid]["questions"].append({
                "query": entry.query,
                "hint_triggered": entry.hint_triggered,
                "hint_text": entry.hint_text,
                "interaction_type": entry.interaction_type,
                "retrieved_nodes": [node_label] if node_label else [],
            })

        return [
            {
                "student_id": v["student_id"],
                "total_questions": v["total_questions"],
                "hints_triggered": v["hints_triggered"],
                "unique_topics": len(v["topics"]),
                "questions": v["questions"],
            }
            for v in sorted(student_data.values(), key=lambda x: x["total_questions"], reverse=True)
        ]

    # Keep old methods for backwards compatibility
    def calculate_node_struggle(self, course_id: str) -> list[dict]:
        return self.calculate_node_engagement(course_id)

    def calculate_student_struggle(self, course_id: str) -> list[dict]:
        return self.calculate_student_activity(course_id)
