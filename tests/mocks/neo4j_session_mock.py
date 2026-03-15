import pytest
from contextlib import contextmanager

@pytest.fixture
def mock_neo4j_session_factory(mocker):
    session = mocker.MagicMock()
    tx = mocker.MagicMock()
    
    session.execute_write.side_effect = lambda fn, *args, **kwargs: fn(tx, *args, **kwargs)
    session.execute_read.side_effect = lambda fn, *args, **kwargs: fn(tx, *args, **kwargs)
    
    @contextmanager
    def factory():
        yield session
        
    return factory, session, tx
