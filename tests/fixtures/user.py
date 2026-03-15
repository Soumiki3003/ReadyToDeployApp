import pytest
from polyfactory.factories.pydantic_factory import ModelFactory
from app.models.user import User, UserTrajectory

class UserFactory(ModelFactory[User]):
    __model__ = User

class UserTrajectoryFactory(ModelFactory[UserTrajectory]):
    __model__ = UserTrajectory

    @classmethod
    def retrieved_nodes(cls) -> list[str]:
        return ["node1", "node2"]

    @classmethod
    def scores(cls) -> list[float]:
        return [0.9, 0.8]

    @classmethod
    def hint_triggered(cls) -> bool:
        return False

@pytest.fixture
def user_factory():
    return UserFactory

@pytest.fixture
def user(user_factory):
    return user_factory.build()

@pytest.fixture
def user_trajectory_factory():
    return UserTrajectoryFactory

@pytest.fixture
def user_trajectory(user_trajectory_factory):
    return user_trajectory_factory.build()
