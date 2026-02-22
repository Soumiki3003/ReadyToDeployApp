from dependency_injector.wiring import Provide, inject
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user

from app import controllers
from app.containers import Application

app = Blueprint("auth", __name__)


@app.route("/login", methods=["GET"])
def login_page():
    return render_template("auth/login.html")


@app.route("/login", methods=["POST"])
@inject
def login_submit(
    *,
    auth_controller: controllers.AuthController = Provide[
        Application.controllers.auth_controller
    ],
):
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Email and password are required.", "error")
        return render_template("auth/login.html"), 400

    user = auth_controller.login(email, password)
    if not user:
        flash("Invalid email or password.", "error")
        return render_template("auth/login.html"), 401

    login_user(user)
    return redirect(url_for("course.dashboard"))


@app.route("/register", methods=["GET"])
def register_page():
    return render_template("auth/register.html")


@app.route("/register", methods=["POST"])
@inject
def register_submit(
    *,
    auth_controller: controllers.AuthController = Provide[
        Application.controllers.auth_controller
    ],
):
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "student")

    if not name or not email or not password:
        flash("All fields are required.", "error")
        return render_template("auth/register.html"), 400

    try:
        auth_controller.register(name, email, password, role)
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login_page"))
    except ValueError as e:
        flash(str(e), "error")
        return render_template("auth/register.html"), 400


@app.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return redirect(url_for("auth.login_page"))
