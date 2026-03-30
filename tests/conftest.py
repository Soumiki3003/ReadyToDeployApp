pytest_plugins = [
    "tests.fixtures.user",
    "tests.factories.knowledge",
    "tests.mocks.auth_service_mock",
    "tests.mocks.embedder_mock",
    "tests.mocks.graphrag_mock",
    "tests.mocks.neo4j_session_mock",
    "tests.mocks.knowledge_service_mock",
    "tests.mocks.user_service_mock",
    "tests.mocks.chat_service_mock",
    "tests.mocks.supervisor_agent_service_mock",
]
