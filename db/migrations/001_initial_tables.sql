-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Crawl Jobs Table (Parent table)
CREATE TABLE IF NOT EXISTS crawl_jobs (
    id VARCHAR(40) PRIMARY KEY DEFAULT uuid_generate_v4(),
    start_url VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_urls INTEGER DEFAULT 0,
    processed_urls INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    CONSTRAINT valid_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'aborted')
    )
);

-- URL Nodes Table (Child of crawl_jobs)
CREATE TABLE  IF NOT EXISTS url_nodes (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(40) NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    url VARCHAR(2000) NOT NULL,
    is_external BOOLEAN NOT NULL DEFAULT false,
    status_code SMALLINT,
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT url_unique_per_job UNIQUE (job_id, url)
);

-- URL Edges Table (Relationships between URLs)
CREATE TABLE IF NOT EXISTS url_edges (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(40) NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES url_nodes(id) ON DELETE CASCADE,
    target_id INTEGER NOT NULL REFERENCES url_nodes(id) ON DELETE CASCADE,
    link_type VARCHAR(20) DEFAULT 'hyperlink',
    CONSTRAINT no_self_links CHECK (source_id <> target_id),
    CONSTRAINT edge_unique UNIQUE (job_id, source_id, target_id)
);
-- Speed up common queries
CREATE INDEX idx_crawl_jobs_status ON crawl_jobs(status);
CREATE INDEX idx_url_nodes_job ON url_nodes(job_id);
CREATE INDEX idx_url_nodes_url ON url_nodes(url);
CREATE INDEX idx_url_edges_source ON url_edges(source_id);
CREATE INDEX idx_url_edges_target ON url_edges(target_id);

-- For manual migration system
CREATE TABLE IF NOT EXISTS _migrations (
    version VARCHAR(50) PRIMARY KEY,
    checksum VARCHAR(64) NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);


