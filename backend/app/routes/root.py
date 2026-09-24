from flask import Blueprint, jsonify


root_bp = Blueprint("root", __name__)


@root_bp.route("/", methods=["GET"])
def root():
    return jsonify({
        "message": "Welcome to ResolveSmart API",
        "status": "success"
    })