import logging
from pathlib import Path

from werkzeug.datastructures import FileStorage

from app import schemas, services


class KnowledgeController:
    def __init__(
        self,
        uploads_folder: Path,
        knowledge_service: services.KnowledgeService,
        uploads_service: services.KnowledgeUploadService,
    ):
        self.__logger = logging.getLogger(__name__)
        self.__uploads_folder = uploads_folder
        self.__uploads_service = uploads_service
        self.__knowledge_service = knowledge_service

    def __parse_uploaded_file(self, file: FileStorage):
        self.__logger.info(
            f"Starting file upload processing for: {file.filename if file else 'None'}"
        )

        if file and file.filename:
            filepath = self.__uploads_folder / file.filename
            self.__logger.debug(f"Saving file to: {filepath}")

            try:
                file.save(filepath)
                self.__logger.info(f"📄 File saved successfully: {filepath}")
            except Exception as e:
                self.__logger.error(
                    f"Failed to save file {file.filename}: {e}", exc_info=True
                )
                raise

            try:
                self.__logger.debug(f"Creating knowledge graph from file: {filepath}")
                root_id = self.__knowledge_service.create_knowledge_from_file(filepath)
                self.__logger.info(f"Knowledge graph root created with ID: {root_id}")
            except Exception as e:
                self.__logger.error(
                    f"Failed to create knowledge from file {filepath}: {e}",
                    exc_info=True,
                )
                raise

            try:
                self.__logger.debug(
                    f"Retrieving knowledge graph for root ID: {root_id}"
                )
                knowledge_graph = self.__knowledge_service.get_knowledge(root_id)
                self.__logger.info(
                    f"Knowledge graph retrieved successfully for root ID: {root_id}"
                )
            except Exception as e:
                self.__logger.error(
                    f"Failed to retrieve knowledge graph for root ID {root_id}: {e}",
                    exc_info=True,
                )
                raise

            self.__logger.debug(
                f"Generated KG JSON: \n{knowledge_graph.model_dump_json(indent=2)}"
            )

            return knowledge_graph

        self.__logger.warning("No file or filename provided, returning None")
        return None

    def parse_uploaded_file_list(
        self,
        form: schemas.KnowledgeUploadRequest,
    ) -> schemas.KnowledgeUploadResponse:
        self.__logger.info(
            f"Processing file upload request with {len(form.files)} file(s)"
        )
        self.__logger.debug(f"HTML link: {form.html_link}")

        uploaded_paths = []

        for idx, f in enumerate(form.files, 1):
            self.__logger.debug(
                f"Processing file {idx}/{len(form.files)}: {f.filename if f else 'None'}"
            )

            try:
                knowledge_graph = self.__parse_uploaded_file(f)
                if knowledge_graph:
                    if sources := getattr(knowledge_graph, "sources", None):
                        uploaded_paths.extend(sources)
                        self.__logger.info(
                            f"Successfully processed file {idx}/{len(form.files)}: {sources}"
                        )
                    else:
                        self.__logger.warning(
                            f"Knowledge graph for file {f.filename} has no sources attribute"
                        )
                else:
                    self.__logger.warning(
                        f"Failed to process uploaded file: {f.filename}"
                    )
            except Exception as e:
                self.__logger.error(
                    f"Error processing file {f.filename}: {e}", exc_info=True
                )

        self.__logger.info(
            f"File upload complete. Successfully processed {len(uploaded_paths)}/{len(form.files)} files"
        )

        response = schemas.KnowledgeUploadResponse(
            uploaded=uploaded_paths,
            html_link=form.html_link,
            graph_generated=bool(uploaded_paths),
        )
        self.__logger.debug(
            f"Returning response: graph_generated={response.graph_generated}, uploaded_count={len(uploaded_paths)}"
        )

        return response

    def get_uploads(self, page: int = 1, page_size: int = 10):
        self.__logger.debug(f"Fetching uploads - page: {page}, page_size: {page_size}")

        if page <= 0 or page_size <= 0:
            self.__logger.error(
                f"Invalid pagination parameters: page={page}, page_size={page_size}"
            )
            raise ValueError("Page and page_size must be positive integers")

        offset = (page - 1) * page_size
        self.__logger.debug(
            f"Calculating offset: {offset} (page {page} * size {page_size})"
        )

        try:
            uploads = self.__uploads_service.get_many(limit=page_size, offset=offset)
            self.__logger.debug(
                f"Successfully retrieved {len(uploads) if uploads else 0} uploads"
            )
            return uploads
        except Exception as e:
            self.__logger.error(f"Failed to retrieve uploads: {e}", exc_info=True)
            raise

    def get_knowledge(self, knowledge_id: str):
        self.__logger.debug(f"Fetching knowledge graph for ID: {knowledge_id}")
        if not knowledge_id:
            raise ValueError("knowledge_id is required")
        try:
            return self.__knowledge_service.get_knowledge(knowledge_id)
        except Exception as e:
            self.__logger.error(
                f"Failed to fetch knowledge graph for ID {knowledge_id}: {e}",
                exc_info=True,
            )
            raise

    def get_root_nodes(
        self, page: int = 1, page_size: int = 5
    ) -> list[schemas.KnowledgeRootNode]:
        self.__logger.debug(f"Fetching root nodes (page={page}, page_size={page_size})")
        if page <= 0 or page_size <= 0:
            raise ValueError("Page and page_size must be positive integers")

        try:
            return self.__knowledge_service.get_root_nodes(
                limit=page_size,
                offset=(page - 1) * page_size,
            )
        except Exception as e:
            self.__logger.error(
                f"Failed to retrieve root nodes: {e}",
                exc_info=True,
            )
            raise
