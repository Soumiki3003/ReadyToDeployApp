from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from dependency_injector import containers, providers
import logging.config
from pydantic_ai import Embedder, Agent
from . import gateways, services, controllers
from neo4j_graphrag.retrievers import VectorRetriever
from neo4j_graphrag.generation import GraphRAG
from jinja2 import Environment, FileSystemLoader
from app import models, prompts


@contextmanager
def folder(folderpath: str) -> Generator[Path, None, None]:
    upload_dir = Path(folderpath)
    if not upload_dir.is_dir():
        raise NotADirectoryError(f"Upload path {folderpath} is not a valid directory.")
    upload_dir.mkdir(exist_ok=True)
    yield upload_dir


_ROOT_FOLDER = Path(__file__).parent
_TEMPLATES_FOLDER = _ROOT_FOLDER / "templates"
_STATIC_FOLDER = _ROOT_FOLDER / "static"
_UPLOADS_FOLDER = _STATIC_FOLDER / "uploads"


class Core(containers.DeclarativeContainer):
    config = providers.Configuration()

    logging = providers.Resource(logging.config.dictConfig, config=config.logging)
    static_folder = providers.Singleton(folder, folderpath=_STATIC_FOLDER)
    uploads_folder = providers.Resource(folder, folderpath=_UPLOADS_FOLDER)

    web_templates_folder = providers.Singleton(_TEMPLATES_FOLDER / "web")


class AI(containers.DeclarativeContainer):
    config = providers.Configuration()

    prompt_template_env = providers.Singleton(
        Environment,
        loader=FileSystemLoader(providers.Singleton(_TEMPLATES_FOLDER / "prompts")),
        autoescape=True,
    )

    default_agent = providers.Singleton(
        Agent,
        model=config.agents.default.model.required(),
    )

    default_embedder = providers.Singleton(
        Embedder,
        model=config.embedder.default.model.required(),
    )

    knowledge_file_agent = providers.Singleton(
        Agent,
        model=config.agents.knowledge_file.model.required(),
        system_prompt=providers.Singleton(
            prompts.get_knowledge_system_prompt,
            env=prompt_template_env,
        ),
    )

    graph_agent = providers.Singleton(
        Agent,
        model=config.graph.model.required(),
    )


class Gateways(containers.DeclarativeContainer):
    config = providers.Configuration()
    ai = providers.DependenciesContainer()

    neo4j = providers.Resource(
        gateways.Neo4jDriver,
        uri=config.neo4j.uri,
        user=config.neo4j.user,
        password=config.neo4j.password,
    )

    neo4j_agent = providers.Singleton(
        gateways.Neo4jAgent,
        model_name=ai.config.default.model.required(),
    )

    embedder = providers.Singleton(
        Embedder,
        model=config.embedding.graph.model,
    )
    neo4j_embedder = providers.Singleton(
        gateways.Neo4jEmbedder,
        embedder=embedder,
    )

    # TODO: Add a prompt template
    trajectory_graphrag = providers.Singleton(
        GraphRAG,
        retriever=providers.Factory(
            VectorRetriever,
            driver=neo4j.provided.driver,
            embedder=neo4j_embedder,
            index_name=config.rag.indexes.trajectory.required(),
            database=neo4j.provided.neo4j_database,
        ),
        llm=neo4j_agent,
    )


class Controllers(containers.DeclarativeContainer):
    config = providers.Configuration()
    core = providers.DependenciesContainer()

    knowledge_controller = providers.Factory(
        controllers.KnowledgeController,
        uploads_folder=core.uploads_folder,
    )


class Services(containers.DeclarativeContainer):
    config = providers.Configuration()

    ai = providers.DependenciesContainer()
    gateways = providers.DependenciesContainer()
    prompts = providers.DependenciesContainer()

    file = providers.Factory(services.FileService)
    knowledge = providers.Factory(
        services.KnowledgeService,
        session_factory=gateways.neo4j.provided.session,
        graph_rag=gateways.trajectory_graphrag,
        file_service=file,
        agent=ai.knowledge_file_agent,
    )


class Application(containers.DeclarativeContainer):
    config = providers.Configuration(
        yaml_files=[Path(__file__).parents[1] / "config.yaml"], strict=True
    )

    core = providers.Container(Core, config=config.core)
    ai = providers.Container(AI, config=config.agents)
    gateways = providers.Container(Gateways, config=config.gateways, ai=ai)

    services = providers.Container(
        Services, config=config, gateways=gateways, core=core
    )
    controllers = providers.Container(Controllers, config=config, core=core)
