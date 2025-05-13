from flask import Flask, render_template, request, redirect, abort
from posthog import Posthog
from src.database import run_migrations, SessionLocal
from src.models import CrawlJob, UrlNode
from src.routes.jobs import jobs_bp
from src.routes.graph import graph_bp
from src.routes.sitemap.sitemap_parser import sitemap_parser_bp
from src.security import configure_security
from src.tasks.crawler import crawl_website
import logging
import uuid


logger = logging.getLogger("App")


def create_app():
    logger.info(f"Start application: {__name__}")
    app = Flask(__name__)

    # Update database
    run_migrations()

    # Configuration
    app.config.update(
        {"JSON_SORT_KEYS": False, "SECRET_KEY": "your-secret-key-here"}
    )

    # Register blueprints
    app.register_blueprint(sitemap_parser_bp, url_prefix="/api/v1")
    app.register_blueprint(jobs_bp, url_prefix="/api/v1")
    app.register_blueprint(graph_bp, url_prefix="/api/v1")

    @app.route("/", methods=["GET"])
    def index():
        return render_template("sitemap-parser.html")

    @app.route("/jobs", methods=["GET"])
    def jobs_list():
        return render_template("jobs.html")

    @app.route("/graph/<job_id>", methods=["GET"])
    def graph_page(job_id):
        return render_template("graph.html", job_id=job_id)

    @app.route("/crawl-urls", methods=["GET", "POST"])
    def start_crawl():
        if request.method == "POST":
            url = request.form["url"]
            db = SessionLocal()

            try:
                # 1. Create job record FIRST
                job = CrawlJob(
                    id=str(uuid.uuid4()),  # Generate UUID before task
                    start_url=url,
                    status="pending",
                )
                db.add(job)
                db.commit()  # Ensure job exists in DB

                # 2. Start async task AFTER commit
                crawl_website.apply_async(
                    args=[url], task_id=job.id
                )  # Use same ID

                # 3. Redirect with confirmed job ID
                return redirect("/urls-results/" + str(job.id))
            except Exception as e:
                db.rollback()
                abort(500, description=str(e))
            finally:
                db.close()

        return render_template("crawler_start.html")

    @app.route("/urls-results/<job_id>")
    def url_results(job_id):
        db = SessionLocal()

        # Get job metadata
        job = db.query(CrawlJob).filter_by(id=job_id).first()

        # Query graph data on-demand
        internal_urls = (
            db.query(UrlNode.url)
            .filter_by(job_id=job_id, is_external=False)
            .limit(200)
            .all()
        )

        external_urls = (
            db.query(UrlNode.url)
            .filter_by(job_id=job_id, is_external=True)
            .limit(200)
            .all()
        )

        progress = (
            round((job.processed_urls / job.total_urls * 100), 2)
            if job.total_urls > 0
            else 0
        )

        return render_template(
            "crawler_results.html",
            job_id=job_id,
            status=job.status,
            progress=progress,
            start_url=job.start_url,
            processed_urls=job.processed_urls,
            total_urls=job.total_urls,
            internal_urls=[
                u[0] for u in internal_urls
            ],  # Extract URLs from query results
            external_urls=[u[0] for u in external_urls],
            internal_count=db.query(UrlNode)
            .filter_by(job_id=job_id, is_external=False)
            .count(),
            external_count=db.query(UrlNode)
            .filter_by(job_id=job_id, is_external=True)
            .count(),
        )

    # Security setup
    configure_security(app)

    return app


posthog = Posthog(
    "phc_Xrw2try3KMqtCStlVVUqvjR2BAx9duC9TCyCXJpv6M9",
    host="https://us.i.posthog.com",
)
posthog.debug = True
app = create_app()
