import logging
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app import models, schemas, services


class CourseController:
    def __init__(
        self,
        knowledge_service: services.KnowledgeService,
        user_service: services.UserService,
        chat_service: services.ChatService,
        supervisor_agent_service: services.SupervisorAgentService,
        uploads_folder: Path,
        uploads_service: services.KnowledgeUploadService,
    ):
        self.__logger = logging.getLogger(__name__)
        self.__knowledge_service = knowledge_service
        self.__user_service = user_service
        self.__chat_service = chat_service
        self.__supervisor_agent_service = supervisor_agent_service
        self.__uploads_folder = uploads_folder
        self.__uploads_service = uploads_service

    def get_courses(
        self,
        params: schemas.PaginatedCourses,
    ) -> tuple[list[schemas.KnowledgeRootNode], bool]:
        self.__logger.debug(
            f"Fetching courses (page={params.page}, page_size={params.page_size})"
        )

        root_nodes = self.__knowledge_service.get_root_nodes(
            limit=params.page_size + 1,
            offset=(params.page - 1) * params.page_size,
            user_id=params.user_id,
            user_role=params.user_role,
        )
        has_next = len(root_nodes) > params.page_size
        courses = root_nodes[: params.page_size]
        return courses, has_next

    def create_course(
        self, params: schemas.CreateCourse, creator_id: str | None = None
    ) -> str:
        self.__logger.info(f"Creating course: {params.name}")
        instructor_ids = list(params.instructor_ids)
        if creator_id and creator_id not in instructor_ids:
            instructor_ids.append(creator_id)
        return self.__knowledge_service.create_empty_course(
            params.name,
            params.description,
            instructor_ids=instructor_ids,
            student_ids=list(params.student_ids),
        )

    def upload_to_course(self, course_id: str, files: list[FileStorage]) -> int:
        """Save and process each uploaded file.

        Returns the number of files actually processed.
        Raises ValueError if every supplied file was rejected (empty list or all
        filenames reduced to nothing after sanitisation).
        """
        self.__logger.info(f"Uploading {len(files)} file(s) to course {course_id}")
        processed = 0
        for f in files:
            if f and f.filename:
                safe_name = secure_filename(f.filename)
                if not safe_name:
                    self.__logger.warning(
                        f"Rejected upload with unsafe filename: {f.filename!r}"
                    )
                    continue
                filepath = self.__uploads_folder / safe_name
                f.save(filepath)
                self.__logger.info(f"File saved: {filepath}")
                self.__knowledge_service.add_document_to_course(course_id, filepath)
                processed += 1

        if processed == 0:
            raise ValueError("No valid files to process. All filenames were empty or unsafe.")
        return processed

    def get_uploads(self, page: int = 1, page_size: int = 10):
        if page <= 0 or page_size <= 0:
            raise ValueError("Page and page_size must be positive integers")
        offset = (page - 1) * page_size
        return self.__uploads_service.get_many(limit=page_size, offset=offset)

    def get_course(self, course_id: str):
        self.__logger.debug(f"Fetching course: {course_id}")
        return self.__knowledge_service.get_knowledge(course_id)

    def get_course_members(
        self, course_id: str
    ) -> dict[str, list[schemas.CourseMember]]:
        return self.__knowledge_service.get_course_members(course_id)

    def update_course_members(
        self, course_id: str, params: schemas.UpdateCourseMembers
    ) -> None:
        self.__logger.info(f"Updating members for course {course_id}")
        self.__knowledge_service.set_course_instructors(
            course_id, params.instructor_ids
        )
        self.__knowledge_service.set_course_students(course_id, params.student_ids)

    def get_users_by_role(self, role: str) -> list[schemas.CourseMember]:
        users = self.__user_service.get_users_by_role(role)
        return [
            schemas.CourseMember(id=u.id, name=u.name, email=u.email, role=u.role.value)
            for u in users
        ]

    def clear_course(self, course_id: str) -> None:
        self.__logger.info(f"Clearing course: {course_id}")
        self.__knowledge_service.clear_course(course_id)

    def chat_send(
        self, user_id: str, course_id: str, message: str
    ) -> schemas.ChatResponse:
        self.__logger.info(
            f"Processing chat message for user {user_id} in course {course_id}"
        )

        history = self.__chat_service.get_messages(user_id, course_id)
        llm_messages = self.__chat_service.to_llm_messages(history)

        self.__chat_service.add_message(
            user_id,
            course_id,
            models.ChatMessage(role=models.ChatMessageRole.USER, content=message),
        )

        result = self.__supervisor_agent_service.retrieve_context(
            user_id, message, course_id, message_history=llm_messages
        )

        answer = (
            result.answer
            if result
            else self.__supervisor_agent_service.RESPONSE_FALLBACK
        )
        hint_text = result.hint_text if result else None

        self.__chat_service.add_message(
            user_id,
            course_id,
            models.ChatMessage(role=models.ChatMessageRole.ASSISTANT, content=answer),
        )

        return schemas.ChatResponse(answer=answer, hint_text=hint_text)

    def get_pending_hints(self, course_id: str):
        return self.__user_service.get_pending_hints(course_id)

    def update_hint_approval(
        self,
        trajectory_id: str,
        status: models.HintApprovalStatus,
        *,
        hint_text: str | None = None,
    ):
        return self.__user_service.update_hint_approval(
            trajectory_id, status, hint_text=hint_text
        )

    def get_approved_hints(self, user_id: str, course_id: str):
        return self.__user_service.get_approved_hints_for_student(user_id, course_id)

    def mark_hint_read(self, trajectory_id: str, course_id: str) -> None:
        self.__user_service.mark_hint_read(trajectory_id, course_id)

    def delete_course(self, course_id: str) -> None:
        self.__logger.info(f"Deleting course: {course_id}")
        self.__knowledge_service.delete_course(course_id)

    def create_manual_hint(self, course_id: str, params: schemas.CreateManualHint) -> None:
        self.__logger.info(f"Instructor creating manual hint for course {course_id}")
        
        target_student_ids = []
        if params.student_id == "all":
            members = self.get_course_members(course_id)
            target_student_ids = [s.id for s in members["students"]]
        else:
            target_student_ids = [params.student_id]
            
        for s_id in target_student_ids:
            trajectory = models.UserTrajectory(
                user_id=s_id,
                course_id=course_id,
                query="Manual Hint from Instructor",
                interaction_type="manual_hint",
                hint_triggered=True,
                hint_reason="Manually created by instructor",
                hint_text=params.hint_text,
                hint_approval_status=models.HintApprovalStatus.APPROVED,
            )
            self.__user_service.add_trajectory_entry(s_id, trajectory)
