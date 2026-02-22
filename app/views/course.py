from dependency_injector.wiring import Provide, inject
from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from flask_pydantic import validate

from app import controllers, schemas
from app.containers import Application
from app.views.guards import roles_required

app = Blueprint("course", __name__)


@app.route("/", methods=["GET"])
@login_required
@validate()
@inject
def dashboard(
    form: schemas.Paginated,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
    allowed_extensions: list[str] = Provide[Application.core.allowed_extensions],
):
    courses, has_next = course_controller.get_courses(form)

    return render_template(
        "course/dashboard.html",
        courses=courses,
        page=form.page,
        page_size=form.page_size,
        has_next=has_next,
        allowed_extensions=allowed_extensions,
    )


@app.route("/course/create", methods=["POST"])
@roles_required("instructor")
@validate()
@inject
def create_course(
    form: schemas.CreateCourse,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    course_id = course_controller.create_course(form.name, form.description)
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
@validate()
@inject
def chat_send(
    course_id: str,
    form: schemas.ChatUserMessageFormRequest,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    # Return user message bubble + assistant response
    # For now, assistant response is a placeholder since SupervisorAgentService
    # requires full infrastructure (Neo4j indexes, Ollama, embeddings)
    try:
        response_text = "I'm processing your question. The full AI assistant will be available once the infrastructure is configured."
    except Exception:
        response_text = "An error occurred while processing your message."

    return render_template(
        "course/chat_message.html",
        user_message=form.content,
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


@app.route("/course/<course_id>/delete", methods=["DELETE"])
@roles_required("instructor")
@inject
def delete_course(
    course_id: str,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    try:
        course_controller.delete_course(course_id)
        return {"success": True, "redirect": "/"}, 200
    except ValueError as e:
        return {"error": str(e)}, 404
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/course/<course_id>/clear", methods=["DELETE"])
@roles_required("instructor")
@inject
def clear_course(
    course_id: str,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    try:
        course_controller.clear_course(course_id)
        return {"success": True}, 200
    except ValueError as e:
        return {"error": str(e)}, 404
    except Exception as e:
        return {"error": str(e)}, 500


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
