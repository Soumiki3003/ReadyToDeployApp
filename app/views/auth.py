from dependency_injector.wiring import Provide, inject
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_user, logout_user
from flask_pydantic import validate

from app import controllers, schemas
from app.containers import Application

app = Blueprint("auth", __name__)


@app.route("/login", methods=["GET"])
def login_page():
    return render_template("auth/login.html")


@app.route("/login", methods=["POST"])
@validate()
@inject
def login_submit(
    form: schemas.LoginRequest,
    *,
    auth_controller: controllers.AuthController = Provide[
        Application.controllers.auth_controller
    ],
):
    user = auth_controller.login(form)
    if not user:
        flash("Invalid email or password.", "error")
        return render_template("auth/login.html"), 401

    login_user(user)
    return redirect(url_for("course.dashboard"))


@app.route("/register", methods=["GET"])
def register_page():
    return render_template("auth/register.html")


@app.route("/register", methods=["POST"])
@validate()
@inject
def register_submit(
    form: schemas.CreateUser,
    *,
    auth_controller: controllers.AuthController = Provide[
        Application.controllers.auth_controller
    ],
):
    try:
        auth_controller.register(form)
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login_page"))
    except ValueError as e:
        flash(str(e), "error")
        return render_template("auth/register.html"), 400


@app.route("/logout", methods=["POST"])
def logout():
    try:
        logout_user()
    except Exception:
        # Force clear the session even if logout fails
        from flask import session

        session.clear()
    return redirect(url_for("auth.login_page"))
