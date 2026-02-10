from pathlib import Path
from werkzeug.datastructures import FileStorage
import logging
from parsers.dual_parser import parse_dualpath
from app import schemas, services

logger = logging.getLogger(__name__)


class KnowledgeController:
    def __init__(
        self,
        uploads_folder: Path,
        knowledge_service: services.KnowledgeService,
    ):
        self.__uploads_folder = uploads_folder
        self.__knowledge_service = knowledge_service

    def __parse_uploaded_file(self, file: FileStorage):
        if file and file.filename:
            filepath = self.__uploads_folder / file.filename
            file.save(filepath)
            logger.debug(f"📄 Uploaded: {filepath}")

            root_id = self.__knowledge_service.create_knowledge_from_file(filepath)
            knowledge_graph = self.__knowledge_service.get_knowledge(root_id)

            logger.debug(
                f"Generated KG JSON: \n{knowledge_graph.model_dump_json(indent=2)}"
            )

            return knowledge_graph
        return None

    def parse_uploaded_file_list(
        self,
        form: schemas.KnowledgeUploadRequest,
    ) -> schemas.KnowledgeUploadResponse:
        uploaded_paths = []

        for f in form.files:
            knowledge_graph = self.__parse_uploaded_file(f)
            if knowledge_graph:
                uploaded_paths.append(knowledge_graph.source)
            else:
                logger.warning(f"Failed to process uploaded file: {f.filename}")

        return schemas.KnowledgeUploadResponse(
            uploaded=uploaded_paths,
            html_link=form.html_link,
            graph_generated=bool(uploaded_paths),
        )
