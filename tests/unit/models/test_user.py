import pytest
from app.models.user import User, UserRole, UserTrajectory, HintApprovalStatus

def test_user_properties(user):
    assert user.get_id() == user.id
    assert user.is_active == user.enabled

def test_user_trajectory_valid(user_trajectory):
    assert user_trajectory.id is not None
    assert user_trajectory.timestamp is not None
    assert user_trajectory.query is not None

def test_user_trajectory_validation():
    with pytest.raises(ValueError, match="Length of scores must match"):
        UserTrajectory(
            user_id="user_123",
            query="test",
            interaction_type="test",
            retrieved_nodes=["a"],
            scores=[]
        )

def test_user_trajectory_hint_validation():
    with pytest.raises(ValueError, match="hint_reason must be provided"):
        UserTrajectory(
            user_id="user_123",
            query="test",
            interaction_type="test",
            hint_triggered=True
        )
    
    with pytest.raises(ValueError, match="hint_text must be provided"):
        UserTrajectory(
            user_id="user_123",
            query="test",
            interaction_type="test",
            hint_triggered=True,
            hint_reason="test reason"
        )

def test_user_trajectory_hint_success():
    trajectory = UserTrajectory(
        user_id="user_123",
        query="test",
        interaction_type="test",
        hint_triggered=True,
        hint_reason="test reason",
        hint_text="test text"
    )
    assert trajectory.hint_approval_status == HintApprovalStatus.PENDING
