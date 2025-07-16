from bs4 import BeautifulSoup
from celery import Celery
from datetime import datetime
from robotexclusionrulesparser import RobotExclusionRulesParser
from src.database import SessionLocal
from src.models import CrawlJob, UrlNode, UrlEdge
from urllib.parse import urljoin, urlparse
from src.routes.sitemap.sitemap_parser import get_sitemap_urls
import re
import requests
import time
import logging
import ssl


logger = logging.getLogger("CrawlerTask")
logging.basicConfig(level=logging.INFO)

app = Celery(
    "crawler", broker="redis://redis:6379/0", backend="redis://redis:6379/0"
)


def normalize_url(u):
    logger.info(f"Normalizing url: {u}")
    p = urlparse(u)
    ret = f"{p.scheme}://{p.netloc}{p.path}".rstrip("/")
    logger.debug(f"Normalized URD: {ret}")
    return ret


def process_url(url, job_id, db, robots):
    """Process a single URL and store results"""

    logger.info(f"Processing URL: {url}")
    try:
        # Respect robots.txt rules
        if not robots.is_allowed("*", url):
            logger.info(f"Not allow to parse HTML by robots.txt")
            return set()

        # Respect crawl delay
        time.sleep(robots.get_crawl_delay("*") or 1)

        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        domain = urlparse(url).netloc

        # Create or get URL node
        url_node = db.query(UrlNode).filter_by(url=url, job_id=job_id).first()
        if not url_node:
            url_node = UrlNode(
                job_id=job_id,
                url=url,
                is_external=False,
                status_code=response.status_code,
            )
            db.add(url_node)
            db.flush()
        else:
            # Update status code for existing node
            url_node.status_code = response.status_code

        # Find all links
        links = set()

        # HTML links
        for a in soup.find_all("a", href=True):
            if a["href"].strip() in ("", "#", url):  # Skip common self-links
                continue

            links.add(normalize_url(a["href"]))

        # JavaScript links (static analysis)
        for script in soup.find_all("script"):
            if script.string:
                links.update(
                    re.findall(
                        r"(?:window\.location|href|fetch|axios\.get|url)\s*[=:]\s*['\"]([^'\"]+)",
                        script.string,
                    )
                )

        validLinks = set()
        # Process each link
        for link in links:
            absolute_url = normalize_url(urljoin(url, link))
            parsed = urlparse(absolute_url)

            # Skip self-links before DB operations
            if absolute_url == url:  # Or compare node IDs if already exists
                continue
            is_external = parsed.netloc != domain

            if not is_external:
                validLinks.add(link)

            if url in validLinks:
                continue

            # Create target node
            target_node = (
                db.query(UrlNode)
                .filter_by(url=absolute_url, job_id=job_id)
                .first()
            )
            if not target_node:
                target_node = UrlNode(
                    job_id=job_id,
                    url=absolute_url,
                    is_external=is_external,
                    status_code=None,
                )
                db.add(target_node)
                db.flush()

            # Create edge if not exists
            if (
                not db.query(UrlEdge)
                .filter_by(
                    job_id=job_id,
                    source_id=url_node.id,
                    target_id=target_node.id,
                )
                .first()
            ):
                edge = UrlEdge(
                    job_id=job_id,
                    source_id=url_node.id,
                    target_id=target_node.id,
                    link_type="hyperlink",
                )
                db.add(edge)
                db.flush()
            logger.info(
                f"Added link to graph {job_id}: {url_node.id}->{target_node.id}"
            )

        db.commit()
        return validLinks
    except requests.exceptions.Timeout as t:
        logger.info(f"Request timeout for URL {url}: {t}")
        return set()
    except ssl.SSLError as ssl:
        logger.info(f"Request for a invalid SSL URL {url}: {ssl}")
        return set()
    except Exception as e:
        db.rollback()
        raise e


def get_pending_urls(job_id, db, limit=100):
    """Get pending URLs from database with pagination"""
    return db.query(UrlNode).filter_by(
        job_id=job_id, 
        status_code=None
    ).limit(limit).all()


def mark_url_visited(url, job_id, db):
    """Mark URL as visited in database"""
    url_node = db.query(UrlNode).filter_by(url=url, job_id=job_id).first()
    if url_node:
        db.commit()


@app.task(bind=True)
def crawl_website(self, base_url):
    """Main crawl task with improved memory management"""
    db = SessionLocal()
    robots = RobotExclusionRulesParser()
    robots.fetch(
        urlparse(base_url).scheme
        + "://"
        + urlparse(base_url).netloc
        + "/robots.txt"
    )

    domain = urlparse(base_url).netloc
    self.is_aborted = False
    try:
        # Initialize job
        job = db.query(CrawlJob).filter_by(id=self.request.id).first()
        if not job:
            raise ValueError(f"Job {self.request.id} not found")
        
        # Get initial URLs from sitemap
        sitemap_urls = get_sitemap_urls(base_url)
        job.total_urls = len(sitemap_urls)
        job.status = "running"
        db.commit()
        
        # Add initial URLs to database
        for url in sitemap_urls:
            normalized_url = normalize_url(url)
            if urlparse(normalized_url).netloc == domain:
                existing_node = db.query(UrlNode).filter_by(
                    url=normalized_url, job_id=job.id
                ).first()
                if not existing_node:
                    url_node = UrlNode(
                        job_id=job.id,
                        url=normalized_url,
                        is_external=False,
                        status_code=None,
                    )
                    db.add(url_node)
        db.commit()
        
        processed_count = 0
        
        # Process URLs in batches to avoid memory issues
        while True:
            if self.is_aborted:
                job.status = "aborted"
                db.commit()
                return
                
            # Get batch of pending URLs
            pending_urls = get_pending_urls(job.id, db, limit=50)
            if not pending_urls:
                break
                
            for url_node in pending_urls:
                if self.is_aborted:
                    job.status = "aborted"
                    db.commit()
                    return
                    
                url = url_node.url
                if urlparse(url).netloc != domain:
                    continue
                    
                valid_urls = process_url(url, job.id, db, robots)
                mark_url_visited(url, job.id, db)
                processed_count += 1
                
                # Update progress
                job.processed_urls = processed_count
                job.total_urls = db.query(UrlNode).filter_by(job_id=job.id).count()
                db.commit()
                
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": round((processed_count / job.total_urls * 100), 2) if job.total_urls > 0 else 0,
                        "current_url": url,
                        "processed": processed_count,
                        "total": job.total_urls,
                    },
                )
                
                # Add new URLs to database for processing
                for new_url in valid_urls:
                    normalized_new_url = normalize_url(urljoin(url, new_url))
                    if urlparse(normalized_new_url).netloc == domain:
                        existing_node = db.query(UrlNode).filter_by(
                            url=normalized_new_url, job_id=job.id
                        ).first()
                        if not existing_node:
                            new_url_node = UrlNode(
                                job_id=job.id,
                                url=normalized_new_url,
                                is_external=False,
                                status_code=None,
                            )
                            db.add(new_url_node)
                db.commit()

        # Finalize
        job.status = "completed"
        job.finished_at = datetime.now()
        db.commit()

    except Exception as e:
        job.status = "failed"
        db.commit()
        raise e
    finally:
        db.close()


@app.task(bind=True)
def abort_crawl(self, job_id):
    """Abort running crawl"""
    task = crawl_website.AsyncResult(job_id)
    task.abort()
    self.is_aborted = True
    return {"status": "ABORT_REQUESTED"}
