from dependency_injector.wiring import Provide, inject
from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from flask_pydantic import validate

from app import controllers, schemas
from app.schemas.knowledge import ALLOWED_CHILDREN, BLOOM_LEVELS
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
    paginated_courses = schemas.PaginatedCourses(
        page=form.page,
        page_size=form.page_size,
        user_id=current_user.id,
        user_role=current_user.role.value,
    )
    courses, has_next = course_controller.get_courses(paginated_courses)
    all_instructors = course_controller.get_users_by_role("instructor")
    all_students = course_controller.get_users_by_role("student")

    return render_template(
        "course/dashboard.html",
        courses=courses,
        page=form.page,
        page_size=form.page_size,
        has_next=has_next,
        allowed_extensions=allowed_extensions,
        all_instructors=all_instructors,
        all_students=all_students,
    )


@app.route("/course/create", methods=["POST"])
@roles_required("instructor")
@validate()
@inject
def create_course(
    body: schemas.CreateCourse,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    course_id = course_controller.create_course(body, creator_id=current_user.id)
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
    try:
        result = course_controller.chat_send(current_user.id, course_id, form.content)
    except Exception:
        result = schemas.ChatResponse(
            answer="An error occurred while processing your message."
        )

    return render_template(
        "course/chat_message.html",
        user_message=form.content,
        assistant_message=result.answer,
        hint_text=result.hint_text,
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
    members = course_controller.get_course_members(course_id)
    all_instructors = course_controller.get_users_by_role("instructor")
    all_students = course_controller.get_users_by_role("student")
    return render_template(
        "course/settings.html",
        course=course,
        course_id=course_id,
        uploads=uploads,
        allowed_extensions=allowed_extensions,
        allowed_children=ALLOWED_CHILDREN,
        bloom_levels=BLOOM_LEVELS,
        members=members,
        all_instructors=all_instructors,
        all_students=all_students,
    )


@app.route("/course/<course_id>/members", methods=["PUT"])
@roles_required("instructor")
@validate()
@inject
def update_members(
    course_id: str,
    body: schemas.UpdateCourseMembers,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    try:
        course_controller.update_course_members(course_id, body)
        return {"success": True}, 200
    except ValueError as e:
        return {"error": str(e)}, 404
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/course/<course_id>/members", methods=["GET"])
@roles_required("instructor")
@inject
def get_members(
    course_id: str,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    members = course_controller.get_course_members(course_id)
    return jsonify(
        {
            "instructors": [
                m.model_dump(mode="json", by_alias=True) for m in members["instructors"]
            ],
            "students": [
                m.model_dump(mode="json", by_alias=True) for m in members["students"]
            ],
        }
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


@app.route("/course/<course_id>/hints", methods=["GET"])
@roles_required("instructor")
@inject
def get_hints(
    course_id: str,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    """Return the pending-hints partial for the instructor settings page."""
    hints = course_controller.get_pending_hints(course_id)
    return render_template(
        "course/hint_item.html",
        hints=hints,
        course_id=course_id,
    )


@app.route("/course/<course_id>/hints/manual", methods=["POST"])
@roles_required("instructor")
@validate()
@inject
def create_manual_hint(
    course_id: str,
    form: schemas.CreateManualHint,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    """Manually create a hint for a student or all students."""
    try:
        course_controller.create_manual_hint(course_id, form)
        return {"success": True}, 201
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/course/<course_id>/hints/<trajectory_id>", methods=["PUT"])
@roles_required("instructor")
@validate()
@inject
def update_hint(
    course_id: str,
    trajectory_id: str,
    form: schemas.UpdateHintApprovalRequest,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    """Approve or reject a hint; returns the updated single-hint card."""
    try:
        # Strip blank-only edits so an empty textarea doesn't overwrite the text
        hint_text = form.hint_text.strip() if form.hint_text else None
        trajectory = course_controller.update_hint_approval(
            trajectory_id, form.status, hint_text=hint_text or None
        )
        if not trajectory:
            return {"error": "Hint not found"}, 404
        return render_template(
            "course/hint_item.html",
            hints=[],  # empty list signals the row should be removed
            course_id=course_id,
        )
    except ValueError as e:
        return {"error": str(e)}, 400
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/course/<course_id>/hints/student/count", methods=["GET"])
@login_required
@inject
def student_hints_count(
    course_id: str,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    """Return the hint-badge count fragment (HTMX polling target)."""
    hints = course_controller.get_approved_hints(current_user.id, course_id)
    return render_template("course/hint_badge.html", count=len(hints))


@app.route("/course/<course_id>/hints/student", methods=["GET"])
@login_required
@inject
def student_hints(
    course_id: str,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    """Return a single approved hint at the requested index (HTMX modal body)."""
    index = request.args.get("index", 0, type=int)
    hints = course_controller.get_approved_hints(current_user.id, course_id)
    total = len(hints)
    hint = hints[index] if hints and 0 <= index < total else None
    return render_template(
        "course/approved_hints.html",
        hint=hint,
        index=index,
        total=total,
        course_id=course_id,
    )


@app.route("/course/<course_id>/hints/<trajectory_id>/read", methods=["POST"])
@login_required
@inject
def mark_hint_read(
    course_id: str,
    trajectory_id: str,
    *,
    course_controller: controllers.CourseController = Provide[
        Application.controllers.course_controller
    ],
):
    """Mark a hint as read the first time the student views it."""
    course_controller.mark_hint_read(trajectory_id, course_id)
    return "", 204


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
        processed = course_controller.upload_to_course(course_id, files)
        return {"success": True, "processed": processed}, 200
    except ValueError as e:
        return {"error": str(e)}, 400
    except Exception as e:
        return {"error": str(e)}, 500
