let currentJobId = null;

async function startCrawl() {
  const url = document.getElementById('crawl-url').value;
  const response = await fetch('/api/v1/crawl', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: url }),
  });

  const data = await response.json();
  currentJobId = data.job_id;
  document.getElementById('abort-btn').style.display = 'block';
  pollProgress();
}

async function pollProgress() {
  const response = await fetch(`/api/v1/crawl/${currentJobId}/progress`);
  const { status, progress, processed, total } = await response.json();

  document.getElementById('progress-bar').style.width = `${progress}%`;
  document.getElementById('status-text').innerText = status;
  document.getElementById('progress-text').innerText =
    `${progress}% (${processed}/${total} URLs)`;

  if (status === 'RUNNING') {
    setTimeout(pollProgress, 2000);
  } else {
    document.getElementById('abort-btn').style.display = 'none';
  }
}

async function abortCrawl() {
  await fetch(`/api/v1/crawl/${currentJobId}/abort`, { method: 'POST' });
}
