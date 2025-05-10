from flask import render_template, request, redirect, url_for
from src.tasks.crawler import crawl_website
from src.database import SessionLocal
from src.models import CrawlJob


@app.route("/crawl-urls", methods=["GET", "POST"])
def start_crawl():
    if request.method == "POST":
        url = request.form["url"]

        # Start crawl and redirect to results page
        task = crawl_website.apply_async(args=[url])
        return redirect(url_for("urls-results", job_id=task.id))

    return render_template("crawler_start.html")


@app.route("/urls-results/<job_id>")
def show_results(job_id):
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
