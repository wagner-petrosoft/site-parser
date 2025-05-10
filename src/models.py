from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

# from src.database import Base
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"
    id = Column(String, primary_key=True)
    start_url = Column(String, nullable=False)
    status = Column(String, default="PENDING")
    total_urls = Column(Integer, default=0)
    processed_urls = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))


class UrlNode(Base):
    __tablename__ = "url_nodes"
    id = Column(Integer, primary_key=True)
    job_id = Column(String, ForeignKey("crawl_jobs.id"))
    url = Column(String, nullable=False)
    is_external = Column(Boolean, default=False)
    status_code = Column(Integer)


class UrlEdge(Base):
    __tablename__ = "url_edges"
    id = Column(Integer, primary_key=True)
    job_id = Column(String, ForeignKey("crawl_jobs.id"))
    source_id = Column(Integer, ForeignKey("url_nodes.id"))
    target_id = Column(Integer, ForeignKey("url_nodes.id"))
    link_type = Column(String)
