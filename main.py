# === app.py ===
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager

from app.containers import Application
from app.views import auth, course, knowledge


login_manager = LoginManager()
login_manager.login_view = "auth.login_page"


@login_manager.user_loader
def load_user(user_id: str):
    try:
        container = Application()
        user_service = container.services.user()
        return user_service.get_user(user_id)
    except Exception:
        return None


def create_app():
    container = Application()
    container.init_resources()
    container.wire(
        modules=[
            "app.views.knowledge",
            "app.views.auth",
            "app.views.course",
        ]
    )

    app = Flask(__name__)
    app.template_folder = Path(__file__).parent / "app" / "templates" / "web"
    app.secret_key = container.config.flask.secret_key()
    app.container = container

    login_manager.init_app(app)

    app.register_blueprint(knowledge.app, url_prefix="/knowledge")
    app.register_blueprint(auth.app, url_prefix="/auth")
    app.register_blueprint(course.app, url_prefix="/")

    return app


def main():
    load_dotenv()
    create_app().run(debug=True)


# === Run Server ===
if __name__ == "__main__":
    main()
