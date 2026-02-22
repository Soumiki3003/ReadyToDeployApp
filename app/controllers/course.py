import logging
from pathlib import Path

from werkzeug.datastructures import FileStorage

from app import schemas, services


class CourseController:
    def __init__(
        self,
        knowledge_service: services.KnowledgeService,
        uploads_folder: Path,
        uploads_service: services.KnowledgeUploadService,
    ):
        self.__logger = logging.getLogger(__name__)
        self.__knowledge_service = knowledge_service
        self.__uploads_folder = uploads_folder
        self.__uploads_service = uploads_service

    def get_courses(
        self, page: int = 1, page_size: int = 12
    ) -> tuple[list[schemas.KnowledgeRootNode], bool]:
        self.__logger.debug(f"Fetching courses (page={page}, page_size={page_size})")
        if page <= 0 or page_size <= 0:
            raise ValueError("Page and page_size must be positive integers")

        root_nodes = self.__knowledge_service.get_root_nodes(
            limit=page_size + 1,
            offset=(page - 1) * page_size,
        )
        has_next = len(root_nodes) > page_size
        courses = root_nodes[:page_size]
        return courses, has_next

    def create_course(self, name: str, description: str = "") -> str:
        self.__logger.info(f"Creating course: {name}")
        return self.__knowledge_service.create_empty_course(name, description)

    def upload_to_course(self, course_id: str, files: list[FileStorage]) -> None:
        self.__logger.info(f"Uploading {len(files)} file(s) to course {course_id}")
        for f in files:
            if f and f.filename:
                filepath = self.__uploads_folder / f.filename
                f.save(filepath)
                self.__logger.info(f"File saved: {filepath}")
                self.__knowledge_service.add_document_to_course(course_id, filepath)

    def get_uploads(self, page: int = 1, page_size: int = 10):
        if page <= 0 or page_size <= 0:
            raise ValueError("Page and page_size must be positive integers")
        offset = (page - 1) * page_size
        return self.__uploads_service.get_many(limit=page_size, offset=offset)

    def get_course(self, course_id: str):
        self.__logger.debug(f"Fetching course: {course_id}")
        return self.__knowledge_service.get_knowledge(course_id)
