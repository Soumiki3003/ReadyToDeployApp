import pytest
from datetime import datetime, timezone
from app.services.dashboard import DashboardService
from app.models.user import UserTrajectory


@pytest.fixture
def dashboard_service(mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    return DashboardService(session_factory=factory)


# ---------- Helpers ----------


def _traj_props(
    *,
    query_repeat_count: int = 0,
    hint_triggered: bool = False,
    response_time_sec: float = 0.0,
    retrieved_nodes: list[str] | None = None,
) -> dict:
    return {
        "id": "traj_id",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": "test query",
        "retrieved_nodes": retrieved_nodes or [],
        "scores": [1.0] * len(retrieved_nodes or []),
        "interaction_type": "chat",
        "query_repeat_count": query_repeat_count,
        "node_entry_count": 0,
        "response_time_sec": response_time_sec,
        "hint_triggered": hint_triggered,
        "hint_reason": "reason" if hint_triggered else None,
        "hint_text": "text" if hint_triggered else None,
        "hint_approval_status": None,
        "hint_read_when": None,
        "course_id": "course1",
    }


def _make_trajectory(
    *,
    user_id: str = "u1",
    query_repeat_count: int = 0,
    hint_triggered: bool = False,
    response_time_sec: float = 0.0,
    retrieved_nodes: list[str] | None = None,
) -> UserTrajectory:
    nodes = retrieved_nodes or []
    return UserTrajectory(
        user_id=user_id,
        query="test",
        retrieved_nodes=nodes,
        scores=[1.0] * len(nodes),
        interaction_type="chat",
        query_repeat_count=query_repeat_count,
        response_time_sec=response_time_sec,
        hint_triggered=hint_triggered,
        hint_reason="reason" if hint_triggered else None,
        hint_text="text" if hint_triggered else None,
    )


# ---------- Struggle formula tests ----------


def test_struggle_formula_basic():
    """(2*2) + 3 + min(30/10, 3) = 10."""
    entry = _make_trajectory(
        user_id="u1", query_repeat_count=2,
        hint_triggered=True, response_time_sec=30.0,
        retrieved_nodes=["n1"],
    )
    assert DashboardService._struggle(entry) == pytest.approx(10.0)


def test_struggle_formula_no_hint():
    """(1*2) + 0 + min(5/10, 3) = 2.5."""
    entry = _make_trajectory(
        user_id="u1", query_repeat_count=1,
        hint_triggered=False, response_time_sec=5.0,
        retrieved_nodes=["n1"],
    )
    assert DashboardService._struggle(entry) == pytest.approx(2.5)


def test_struggle_formula_response_time_capped():
    """Response time contribution capped at 3."""
    entry = _make_trajectory(
        user_id="u1", query_repeat_count=0,
        hint_triggered=False, response_time_sec=999.0,
        retrieved_nodes=["n1"],
    )
    assert DashboardService._struggle(entry) == pytest.approx(3.0)


def test_struggle_formula_zero_values():
    entry = _make_trajectory(
        user_id="u1", query_repeat_count=0,
        hint_triggered=False, response_time_sec=0.0,
        retrieved_nodes=["n1"],
    )
    assert DashboardService._struggle(entry) == pytest.approx(0.0)


# ---------- Node aggregation tests ----------


def test_node_aggregation_groups_by_retrieved_nodes(
    dashboard_service, mock_neo4j_session_factory
):
    factory, session, tx = mock_neo4j_session_factory
    tx.run.return_value.__iter__.return_value = [
        {
            "t": _traj_props(
                query_repeat_count=1, hint_triggered=False,
                response_time_sec=10.0, retrieved_nodes=["n1", "n2"],
            ),
            "user_id": "u1",
        },
        {
            "t": _traj_props(
                query_repeat_count=3, hint_triggered=True,
                response_time_sec=20.0, retrieved_nodes=["n1"],
            ),
            "user_id": "u2",
        },
    ]
    result = dashboard_service.calculate_node_struggle("course1")
    by_node = {r["node_id"]: r["struggle"] for r in result}
    # n1: u1(2+0+1=3) + u2(6+3+2=11) = 14
    # n2: u1(2+0+1=3) = 3
    assert by_node["n1"] == pytest.approx(14.0)
    assert by_node["n2"] == pytest.approx(3.0)


# ---------- Student aggregation tests ----------


def test_student_aggregation_groups_by_user_id(
    dashboard_service, mock_neo4j_session_factory
):
    factory, session, tx = mock_neo4j_session_factory
    tx.run.return_value.__iter__.return_value = [
        {
            "t": _traj_props(
                query_repeat_count=1, hint_triggered=False,
                response_time_sec=10.0, retrieved_nodes=["n1"],
            ),
            "user_id": "u1",
        },
        {
            "t": _traj_props(
                query_repeat_count=2, hint_triggered=True,
                response_time_sec=0.0, retrieved_nodes=["n2"],
            ),
            "user_id": "u1",
        },
        {
            "t": _traj_props(
                query_repeat_count=0, hint_triggered=False,
                response_time_sec=20.0, retrieved_nodes=["n1"],
            ),
            "user_id": "u2",
        },
    ]
    result = dashboard_service.calculate_student_struggle("course1")
    by_student = {r["student_id"]: r["struggle"] for r in result}
    # u1: (2+0+1=3) + (4+3+0=7) = 10
    # u2: (0+0+2=2) = 2
    assert by_student["u1"] == pytest.approx(10.0)
    assert by_student["u2"] == pytest.approx(2.0)


# ---------- Empty course tests ----------


def test_empty_course_returns_empty_node_list(
    dashboard_service, mock_neo4j_session_factory
):
    factory, session, tx = mock_neo4j_session_factory
    tx.run.return_value.__iter__.return_value = []
    assert dashboard_service.calculate_node_struggle("empty") == []


def test_empty_course_returns_empty_student_list(
    dashboard_service, mock_neo4j_session_factory
):
    factory, session, tx = mock_neo4j_session_factory
    tx.run.return_value.__iter__.return_value = []
    assert dashboard_service.calculate_student_struggle("empty") == []
