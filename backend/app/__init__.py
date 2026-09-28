from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

from .config import Config


db = SQLAlchemy()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    from .models import User

    CORS(app)

    from .routes.root import root_bp
    from .routes.health import health_bp
    from .auth.routes import auth_bp

    app.register_blueprint(root_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "status": "error",
            "message": "Resource not found"
        }), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

    return app