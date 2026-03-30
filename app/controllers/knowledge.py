import logging

from app import schemas, services


class KnowledgeController:
    def __init__(
        self,
        knowledge_service: services.KnowledgeService,
        uploads_service: services.KnowledgeUploadService,
    ):
        self.__logger = logging.getLogger(__name__)
        self.__uploads_service = uploads_service
        self.__knowledge_service = knowledge_service

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

    def update_node(self, node_id: str, form: schemas.UpdateNodeRequest) -> None:
        updates = form.model_dump(
            mode="json", by_alias=True, exclude_none=True, exclude={"type"}
        )
        self.__knowledge_service.update_node(node_id, updates)

    def delete_node(self, node_id: str, course_id: str) -> None:
        self.__knowledge_service.delete_node(node_id, course_id)

    def add_child_node(
        self, parent_id: str, form: schemas.CreateChildNodeRequest
    ) -> str:
        props = form.model_dump(mode="json", by_alias=True, exclude={"type"})
        return self.__knowledge_service.add_child_node(parent_id, form.type, props)

    def add_relationship(
        self, node_id: str, form: schemas.CreateRelationshipRequest
    ) -> None:
        self.__knowledge_service.add_relationship(
            node_id, form.to_id, form.relation.value
        )

    def update_relationship(
        self, node_id: str, form: schemas.UpdateRelationshipRequest
    ) -> None:
        self.__knowledge_service.update_relationship(
            node_id, form.to_id, form.old_relation.value, form.new_relation.value
        )

    def delete_relationship(
        self, node_id: str, form: schemas.DeleteRelationshipRequest
    ) -> None:
        self.__knowledge_service.delete_relationship(
            node_id, form.to_id, form.relation.value
        )
