from flask import Flask, render_template
from src.security import configure_security
from src.routes.sitemap.sitemap_parser import sitemap_parser_bp


def create_app():
    app = Flask(__name__)

    # Configuration
    app.config.update(
        {"JSON_SORT_KEYS": False, "SECRET_KEY": "your-secret-key-here"}
    )

    # Register blueprints
    app.register_blueprint(sitemap_parser_bp, url_prefix="/api/v1")

    @app.route("/", methods=["GET"])
    def index():
        return render_template("sitemap-parser.html")

    # Security setup
    configure_security(app)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
