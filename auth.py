from functools import wraps
from flask import abort, g, redirect, url_for
from flask_jwt_extended import (JWTManager,get_jwt_identity,jwt_required,verify_jwt_in_request,)
from models import Users

jwt = JWTManager()

def init_jwt(app):
    jwt.init_app(app)


def get_current_user():
    if hasattr(g, "current_user"):
        return g.current_user

    identity = get_jwt_identity()

    if identity is None:
        return None

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None

    user = Users.query.filter_by(user_id=user_id).first()

    g.current_user = user

    return user


def db_user_by_id(user_id):
    return Users.query.filter_by(user_id=user_id).first()


def role_required(*allowed_roles):
    def decorator(view_function):
        @wraps(view_function)
        @jwt_required()
        def wrapped(*args, **kwargs):
            user = get_current_user()

            if user is None:
                abort(401)

            if user.role not in allowed_roles:
                abort(403)

            g.current_user = user

            return view_function(*args, **kwargs)

        return wrapped

    return decorator