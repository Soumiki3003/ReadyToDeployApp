from dependency_injector.wiring import Provide, inject
from flask import Blueprint, render_template, request
from flask_pydantic import validate
from pydantic import TypeAdapter, ValidationError

from app import controllers, schemas
from app.containers import Application
from app.views.guards import roles_required

_update_node_adapter = TypeAdapter(schemas.UpdateNodeRequest)
_create_child_adapter = TypeAdapter(schemas.CreateChildNodeRequest)

app = Blueprint("knowledge", __name__)


@app.route("/upload/list", methods=["GET"])
@validate()
@inject
def upload_list(
    query: schemas.Paginated,
    *,
    knowledge_controller: controllers.KnowledgeController = Provide[
        Application.controllers.knowledge_controller
    ],
):
    uploads = knowledge_controller.get_uploads(
        page=query.page, page_size=query.page_size
    )

    return render_template(
        "knowledge/upload_list.html",
        uploads=uploads,
    )


@app.route("/graph/data/<knowledge_id>", methods=["GET"])
@validate(response_by_alias=True)
@inject
def graph_data(
    knowledge_id: str,
    *,
    knowledge_controller: controllers.KnowledgeController = Provide[
        Application.controllers.knowledge_controller
    ],
):
    knowledge = knowledge_controller.get_knowledge(knowledge_id)
    return knowledge


# ── Node operations ──


@app.route("/node/<node_id>", methods=["PUT"])
@roles_required("instructor")
@inject
def update_node(
    node_id: str,
    *,
    knowledge_controller: controllers.KnowledgeController = Provide[
        Application.controllers.knowledge_controller
    ],
):
    try:
        body = _update_node_adapter.validate_python(request.get_json())
    except ValidationError as e:
        return {"error": e.errors()}, 422

    try:
        knowledge_controller.update_node(node_id, body)
        return {"success": True}, 200
    except ValueError as e:
        return {"error": str(e)}, 404
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/node/<node_id>", methods=["DELETE"])
@roles_required("instructor")
@inject
def delete_node(
    node_id: str,
    *,
    knowledge_controller: controllers.KnowledgeController = Provide[
        Application.controllers.knowledge_controller
    ],
):
    course_id = request.args.get("course_id", "")
    try:
        knowledge_controller.delete_node(node_id, course_id)
        return {"success": True}, 200
    except ValueError as e:
        return {"error": str(e)}, 404
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/node/<parent_id>/child", methods=["POST"])
@roles_required("instructor")
@inject
def add_child_node(
    parent_id: str,
    *,
    knowledge_controller: controllers.KnowledgeController = Provide[
        Application.controllers.knowledge_controller
    ],
):
    try:
        body = _create_child_adapter.validate_python(request.get_json())
    except ValidationError as e:
        return {"error": e.errors()}, 422

    try:
        new_id = knowledge_controller.add_child_node(parent_id, body)
        return {"success": True, "id": new_id}, 201
    except ValueError as e:
        return {"error": str(e)}, 400
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/node/<node_id>/relationship", methods=["POST"])
@roles_required("instructor")
@validate()
@inject
def add_relationship(
    node_id: str,
    body: schemas.CreateRelationshipRequest,
    *,
    knowledge_controller: controllers.KnowledgeController = Provide[
        Application.controllers.knowledge_controller
    ],
):
    try:
        knowledge_controller.add_relationship(node_id, body)
        return {"success": True}, 201
    except ValueError as e:
        return {"error": str(e)}, 400
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/node/<node_id>/relationship", methods=["PUT"])
@roles_required("instructor")
@validate()
@inject
def update_relationship(
    node_id: str,
    body: schemas.UpdateRelationshipRequest,
    *,
    knowledge_controller: controllers.KnowledgeController = Provide[
        Application.controllers.knowledge_controller
    ],
):
    try:
        knowledge_controller.update_relationship(node_id, body)
        return {"success": True}, 200
    except ValueError as e:
        return {"error": str(e)}, 400
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/node/<node_id>/relationship", methods=["DELETE"])
@roles_required("instructor")
@validate()
@inject
def delete_relationship(
    node_id: str,
    body: schemas.DeleteRelationshipRequest,
    *,
    knowledge_controller: controllers.KnowledgeController = Provide[
        Application.controllers.knowledge_controller
    ],
):
    try:
        knowledge_controller.delete_relationship(node_id, body)
        return {"success": True}, 200
    except ValueError as e:
        return {"error": str(e)}, 400
    except Exception as e:
        return {"error": str(e)}, 500
