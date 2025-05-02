# from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

limiter = Limiter(key_func=get_remote_address)


def configure_security(app):
    # CORS Configuration
    CORS(
        app,
        resources={
            r"/api/v1/parse": {
                "origins": [
                    "https://us-assets.i.posthog.com",
                    "http://localhost:*",  # For development
                ],
                "methods": ["POST"],
                "allow_headers": ["Content-Type"],
            }
        },
    )

    # Talisman Security Headers
    #    Talisman(
    #        app,
    #        content_security_policy={
    #            'default-src': "'self'",
    #            'script-src': [
    #                "'self'",
    #                "https://us-assets.i.posthog.com",
    #                "https://fonts.googleapis.com"
    #            ],
    #            'style-src': [
    #                "'self'",
    #                "https://fonts.googleapis.com",
    #                "'unsafe-inline'"
    #            ],
    #            'font-src': ["'self'", "https://fonts.gstatic.com"]
    #        },
    #        force_https=app.config.get('ENV') == 'production'
    #    )

    # Rate Limiting
    limiter.init_app(app)
    limiter.limit("10/minute")(
        app.view_functions["sitemap_parser.parse_sitemap"]
    )
