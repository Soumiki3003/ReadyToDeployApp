import asyncio
import json
import logging
from contextlib import contextmanager
from typing import Sequence

from neo4j import Driver, GraphDatabase
from neo4j_graphrag.embeddings.base import Embedder as EmbedderInterface
from neo4j_graphrag.llm.base import LLMInterface
from neo4j_graphrag.llm.types import LLMResponse, ToolCall, ToolCallResponse
from neo4j_graphrag.message_history import MessageHistory
from neo4j_graphrag.tool import Tool
from neo4j_graphrag.types import LLMMessage
from pydantic_ai import (
    Agent,
    AgentRunResult,
    Embedder,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelSettings,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    UserContent,
    UserPromptPart,
)
from pydantic_ai import Tool as PydanticAiTool

logger = logging.getLogger(__name__)


@contextmanager
def neo4j_driver(uri: str, *, user: str, password: str):
    auth = (user, password) if user and password else None
    driver = GraphDatabase.driver(uri, auth=auth)
    logger.info(f"Connected to Neo4j at {uri} with user {user}")
    yield driver
    driver.close()
    logger.info("Neo4j driver closed")


@contextmanager
def neo4j_session(driver: Driver, **session_kwargs):
    with driver.session(**session_kwargs) as session:
        yield session


class Neo4jAgent(LLMInterface):
    async def __run_agent(
        self,
        agent: Agent,
        input: list[LLMMessage],
        message_history: list[LLMMessage] | MessageHistory | None = None,
    ) -> AgentRunResult:
        parsed_input: list[UserContent] = [
            message["content"] for message in input if message["role"] == "user"
        ]
        parsed_message_history: list[ModelMessage] = []
        for message in (
            message_history.messages
            if isinstance(message_history, MessageHistory)
            else (message_history or [])
        ):
            role = message["role"]
            content = message["content"]

            if role == "system":
                agent_message = ModelRequest(
                    parts=[SystemPromptPart(content)],
                )
            elif role == "user":
                agent_message = ModelRequest(
                    parts=[UserPromptPart(content)],
                )
            elif role == "assistant":
                agent_message = ModelResponse(
                    parts=[TextPart(content)],
                )
            else:
                raise ValueError(f"Invalid message role: {role}")
            parsed_message_history.append(agent_message)

        return await self._rate_limit_handler.handle_async(agent.run)(
            parsed_input,
            message_history=parsed_message_history,
        )

    def invoke(
        self,
        input: str,
        message_history: list[LLMMessage] | MessageHistory | None = None,
        system_instruction: str | None = None,
    ) -> LLMResponse:
        return asyncio.run(self.ainvoke(input, message_history, system_instruction))

    async def ainvoke(
        self,
        input: str,
        message_history: list[LLMMessage] | MessageHistory | None = None,
        system_instruction: str | None = None,
    ) -> LLMResponse:
        agent = Agent(
            self.model_name,
            system_prompt=system_instruction or (),
            model_settings=ModelSettings(**self.model_params) or None,
        )
        parsed_input = [LLMMessage(role="user", content=input)]

        result = await self.__run_agent(agent, parsed_input, message_history)
        return LLMResponse(content=result.output)

    async def ainvoke_with_tools(
        self,
        input: str,
        tools: Sequence[Tool],
        message_history: list[LLMMessage] | MessageHistory | None = None,
        system_instruction: str | None = None,
    ) -> ToolCallResponse:
        supported_tools = [
            PydanticAiTool.from_schema(
                function=tool.execute,
                name=tool.get_name(),
                description=tool.get_description(),
                json_schema=tool.get_parameters(),
            )
            for tool in tools
        ]

        agent = Agent(
            model=self.model_name,
            model_settings=ModelSettings(**self.model_params) or None,
            system_prompt=system_instruction or (),
            tools=supported_tools,
        )

        result = await self.__run_agent(
            agent, [LLMMessage(role="user", content=input)], message_history
        )
        return ToolCallResponse(
            content=result.output,
            tool_calls=[
                ToolCall(
                    name=part.tool_name,
                    arguments=json.loads(json.dumps(part.args or "{}")),
                )
                for message in result.all_messages()
                for part in message.parts
                if isinstance(part, ToolCallPart)
            ],
        )

    def invoke_with_tools(
        self,
        input: str,
        tools: Sequence[Tool],
        message_history: list[LLMMessage] | MessageHistory | None = None,
        system_instruction: str | None = None,
    ) -> ToolCallResponse:
        return asyncio.run(
            self.ainvoke_with_tools(input, tools, message_history, system_instruction)
        )


class Neo4jEmbedder(EmbedderInterface):
    def __init__(self, embedder: Embedder) -> None:
        self.__embedder = embedder
        super().__init__()

    def embed_query(self, text: str) -> list[float]:
        return list(
            self._rate_limit_handler.handle_sync(self.__embedder.embed_documents_sync)(
                text
            ).embeddings[0]
        )

    async def async_embed_query(self, text: str) -> list[float]:
        result = await self._rate_limit_handler.handle_async(
            self.__embedder.embed_documents
        )(text)
        return list(result.embeddings[0])
