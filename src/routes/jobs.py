from flask import Blueprint, jsonify, request
from src.database import SessionLocal
from src.models import CrawlJob
from src.tasks.crawler import app as celery_app

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/jobs", methods=["GET"])
def list_jobs():
    db = SessionLocal()
    try:
        jobs = db.query(CrawlJob).order_by(CrawlJob.created_at.desc()).all()
        return jsonify(
            [
                {
                    "id": job.id,
                    "start_url": job.start_url,
                    "status": job.status,
                    "created_at": job.created_at.isoformat(),
                    "progress": f"{(job.processed_urls / job.total_urls * 100) if job.total_urls != 0 else 0:.1f}%",
                }
                for job in jobs
            ]
        )
    finally:
        db.close()


@jobs_bp.route("/jobs/<job_id>/stop", methods=["POST"])
def stop_job(job_id):
    celery_app.control.revoke(job_id, terminate=True)
    db = SessionLocal()
    try:
        job = db.query(CrawlJob).filter_by(id=job_id).first()
        if job:
            job.status = "aborted"
            db.commit()
        return jsonify({"status": "success"})
    finally:
        db.close()
