from dependency_injector.wiring import Provide, inject
from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from app import controllers
from app.containers import Application
from app.views.guards import roles_required

app = Blueprint("course", __name__)


@app.route("/", methods=["GET"])
@login_required
@inject
def dashboard(
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
    allowed_extensions: list[str] = Provide[Application.core.allowed_extensions],
):
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 12, type=int)

    courses, has_next = course_controller.get_courses(page=page, page_size=page_size)

    return render_template(
        "course/dashboard.html",
        courses=courses,
        page=page,
        page_size=page_size,
        has_next=has_next,
        allowed_extensions=allowed_extensions,
    )


@app.route("/course/create", methods=["POST"])
@roles_required("instructor")
@inject
def create_course(
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        return {"error": "Course name is required"}, 400

    course_id = course_controller.create_course(name, description)
    return {"id": course_id, "redirect": "/"}, 201


@app.route("/course/<course_id>/chat", methods=["GET"])
@login_required
@inject
def chat(
    course_id: str,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    course = course_controller.get_course(course_id)
    return render_template(
        "course/chat.html",
        course=course,
        course_id=course_id,
        messages=[],
    )


@app.route("/course/<course_id>/chat/send", methods=["POST"])
@login_required
@inject
def chat_send(
    course_id: str,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    message = request.form.get("message", "").strip()
    if not message:
        return "", 400

    # Return user message bubble + assistant response
    # For now, assistant response is a placeholder since SupervisorAgentService
    # requires full infrastructure (Neo4j indexes, Ollama, embeddings)
    try:
        response_text = "I'm processing your question. The full AI assistant will be available once the infrastructure is configured."
    except Exception:
        response_text = "An error occurred while processing your message."

    return render_template(
        "course/chat_message.html",
        user_message=message,
        assistant_message=response_text,
        user_name=current_user.name,
    )


@app.route("/course/<course_id>/settings", methods=["GET"])
@roles_required("instructor")
@inject
def settings(
    course_id: str,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
    allowed_extensions: list[str] = Provide[Application.core.allowed_extensions],
):
    course = course_controller.get_course(course_id)
    uploads = course_controller.get_uploads()
    return render_template(
        "course/settings.html",
        course=course,
        course_id=course_id,
        uploads=uploads,
        allowed_extensions=allowed_extensions,
    )


@app.route("/course/<course_id>/upload", methods=["POST"])
@roles_required("instructor")
@inject
def upload_to_course(
    course_id: str,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    files = request.files.getlist("files")
    if not files:
        return {"error": "No files provided"}, 400

    try:
        course_controller.upload_to_course(course_id, files)
        return {"success": True}, 200
    except Exception as e:
        return {"error": str(e)}, 500
