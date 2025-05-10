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
            return

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


@app.task(bind=True)
def crawl_website(self, base_url):
    """Main crawl task with progress tracking"""
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
        sitemap_urls = set(get_sitemap_urls(base_url))
        job.total_urls = len(sitemap_urls)
        job.status = "running"
        db.commit()
        visitedPages = set()
        # Process each URL
        i = 0
        while len(sitemap_urls) > 0:
            if self.is_aborted:
                job.status = "aborted"
                db.commit()
                return
            url = normalize_url(sitemap_urls.pop())
            if url in visitedPages:
                continue

            if urlparse(url).netloc != domain:
                continue

            validUrlsInPage = process_url(url, job.id, db, robots)
            visitedPages.add(url)
            sitemap_urls.update(validUrlsInPage - visitedPages)
            i = i + 1
            # Update progress
            job.processed_urls = i + 1
            job.total_urls = len(sitemap_urls) + len(visitedPages)
            db.commit()

            self.update_state(
                state="PROGRESS",
                meta={
                    "progress": round((i + 1) / job.total_urls * 100, 2),
                    "current_url": url,
                    "processed": i + 1,
                    "total": job.total_urls,
                },
            )

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
