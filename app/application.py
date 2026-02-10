# === app.py ===
from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap
from flask_pydantic import validate
from app import controllers, schemas
from app.containers import Application
from dependency_injector.wiring import inject, Provide

# === Flask setup ===
root = Flask(__name__)


# === ROUTE: File Upload + Dual Parser ===
@validate()
@inject
def upload(
    form: schemas.KnowledgeUploadRequest,
    *,
    knowledge_controller: controllers.KnowledgeController = Provide[
        Application.controllers.knowledge_controller
    ],
    allowed_extensions: list[str] = Provide[Application.config.core.allowed_extensions],
) -> str | schemas.KnowledgeUploadResponse:
    # TODO: test this generation
    if request.method == "POST":
        return knowledge_controller.parse_uploaded_file_list(request)
    return render_template("upload.html", allowed_extensions=allowed_extensions)


def create_app():
    container = Application()
    container.init_resources()
    container.wire(modules=[__name__])

    app = Flask(__name__)
    app.container = container
    app.add_url_rule("/upload", "upload", upload, methods=["GET", "POST"])

    bootstrap = Bootstrap()
    bootstrap.init_app(app)

    return app


# === Run Server ===
if __name__ == "__main__":
    container = Application()
    create_app().run(debug=True)
