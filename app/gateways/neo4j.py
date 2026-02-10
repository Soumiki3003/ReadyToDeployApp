from contextlib import contextmanager
import logging
from neo4j import Driver, GraphDatabase
import asyncio
from neo4j_graphrag.tool import Tool
from neo4j_graphrag.llm.base import LLMInterface, LLMMessage, MessageHistory
from neo4j_graphrag.utils.rate_limit import RateLimitHandler, DEFAULT_RATE_LIMIT_HANDLER
from neo4j_graphrag.llm.types import LLMResponse
from neo4j_graphrag.embeddings.base import Embedder as EmbedderInterface
import pydantic_ai


logger = logging.getLogger(__name__)


class Neo4jSession:
    def __init__(self, driver: Driver, **session_kwargs):
        self.__driver = driver
        self.__session_kwargs = session_kwargs

    def __enter__(self):
        logger.info("Opening Neo4j session")
        self.__session = self.__driver.session(**self.__session_kwargs)
        return self.__session

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info("Closing Neo4j session")
        self.__session.close()


class Neo4jDriver:
    def __init__(self, uri: str, *, user: str, password: str):
        self.__uri = uri
        self.__user = user
        self.__password = password

    def __enter__(self):
        auth = (
            (self.__user, self.__password) if self.__user and self.__password else None
        )
        self.__driver = GraphDatabase.driver(self.__uri, auth=auth)
        logger.info(f"Connected to Neo4j at {self.__uri} with user {self.__user}")
        return self.__driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__driver.close()
        logger.info("Neo4j driver closed")

    @contextmanager
    def session(self, **session_kwargs):
        with Neo4jSession(self.__driver, **session_kwargs) as session:
            yield session


class Neo4jAgent(LLMInterface):
    async def __run_agent(
        self,
        agent: pydantic_ai.Agent,
        input: list[LLMMessage],
        message_history: list[LLMMessage] | MessageHistory | None = None,
    ):
        parsed_message_history = []
        for message in (
            message_history.messages
            if isinstance(message_history, MessageHistory)
            else (message_history or [])
        ):
            if message.role == "system":
                agent_message = pydantic_ai.ModelMessage(
                    parts=pydantic_ai.SystemPromptPart(message.content),
                )
            elif message.role == "user":
                agent_message = pydantic_ai.ModelMessage(
                    parts=pydantic_ai.UserPromptPart(message.content),
                )
            elif message.role == "assistant":
                agent_message = pydantic_ai.ModelMessage(
                    parts=pydantic_ai.TextPart(message.content),
                )
            else:
                raise ValueError(f"Invalid message role: {message.role}")
            parsed_message_history.append(agent_message)

        async def run() -> LLMResponse:
            response = await agent.run(
                input,
                message_history=parsed_message_history,
            )
            return LLMResponse(
                text=response.output,
            )

        return await self._rate_limit_handler.handle_async(run)

    def invoke(
        self,
        input: list[LLMMessage],
        message_history: list[LLMMessage] | MessageHistory | None = None,
        system_instruction: str | None = None,
    ) -> LLMResponse:
        return asyncio.run(self.ainvoke(input, message_history, system_instruction))

    async def ainvoke(
        self,
        input: list[LLMMessage],
        message_history: list[LLMMessage] | MessageHistory | None = None,
        system_instruction: str | None = None,
    ) -> LLMResponse:
        agent = pydantic_ai.Agent(
            model=self.model_name,
            model_params=self.model_params,
            system_instruction=system_instruction,
            **self.model_params,
        )

        return await self.__run_agent(agent, input, message_history, system_instruction)

    async def ainvoke_with_tools(
        self,
        input: list[LLMMessage],
        tools: list[Tool],
        message_history: list[LLMMessage] | MessageHistory | None = None,
        system_instruction: str | None = None,
    ) -> LLMResponse:
        supported_tools = [
            pydantic_ai.Tool.from_schema(
                tool.execute,
                name=tool.get_name(),
                description=tool.get_description(),
                function_schema=tool.get_parameters(),
            )
            for tool in tools
        ]

        agent = pydantic_ai.Agent(
            model=self.model_name,
            model_params=self.model_params,
            system_instruction=system_instruction,
            tools=supported_tools,
            **self.model_params,
        )

        return await self.__run_agent(agent, input, message_history)

    def invoke_with_tools(
        self,
        input: list[LLMMessage],
        tools: list[Tool],
        message_history: list[LLMMessage] | MessageHistory | None = None,
        system_instruction: str | None = None,
    ) -> LLMResponse:
        return asyncio.run(
            self.ainvoke_with_tools(input, tools, message_history, system_instruction)
        )


class Neo4jEmbedder(EmbedderInterface):
    def __init__(self, embedder: pydantic_ai.Embedder) -> None:
        self.__embedder = embedder
        super().__init__()

    def embed_query(self, text: str) -> list[float]:
        return self.__embedder.embed_sync(text).embeddings[0]

    async def async_embed_query(self, text: str) -> list[float]:
        result = await self.__embedder.embed(text)
        return result.embeddings[0]
