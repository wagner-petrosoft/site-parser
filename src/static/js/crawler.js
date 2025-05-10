let currentJobId = null;
let progressInterval = null;
const RESULTS_LIMIT = 200; // Show first 200 results for performance

// Start a new crawl job
async function startCrawl() {
  const url = document.getElementById('crawl-url').value.trim();
  if (!url) {
    alert('Please enter a valid URL');
    return;
  }

  try {
    // Reset UI
    document.getElementById('progress-container').style.display = 'block';
    document.getElementById('results-container').style.display = 'none';
    document.getElementById('abort-btn').style.display = 'inline-flex';
    document.getElementById('progress-fill').style.width = '0%';
    document.getElementById('status-text').textContent = 'Starting...';
    document.getElementById('progress-text').textContent = '0% (0/0 URLs)';

    // Clear previous results
    document.getElementById('internal-links').innerHTML = '';
    document.getElementById('external-links').innerHTML = '';
    document.getElementById('internal-count').textContent = '0';
    document.getElementById('external-count').textContent = '0';

    // Start crawl
    const response = await fetch('/api/v1/crawl', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url }),
    });

    if (!response.ok) throw new Error('Failed to start crawl');

    const data = await response.json();
    currentJobId = data.job_id;

    // Start polling progress
    progressInterval = setInterval(pollProgress, 2000);
  } catch (error) {
    console.error('Crawl error:', error);
    document.getElementById('status-text').textContent =
      'Error: ' + error.message;
    document.getElementById('abort-btn').style.display = 'none';
  }
}

// Poll for progress updates
async function pollProgress() {
  if (!currentJobId) return;

  try {
    const response = await fetch(`/api/v1/crawl/${currentJobId}/progress`);
    const { status, progress, processed, total } = await response.json();

    // Update UI
    document.getElementById('progress-fill').style.width = `${progress}%`;
    document.getElementById('status-text').textContent =
      status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
    document.getElementById('progress-text').textContent =
      `${progress}% (${processed}/${total} URLs)`;

    // Handle completion
    if (status === 'COMPLETED' || status === 'FAILED' || status === 'ABORTED') {
      clearInterval(progressInterval);
      document.getElementById('abort-btn').style.display = 'none';

      if (status === 'COMPLETED') {
        fetchResults();
      }
    }
  } catch (error) {
    console.error('Progress polling error:', error);
    clearInterval(progressInterval);
  }
}

// Fetch final results
async function fetchResults() {
  try {
    const response = await fetch(`/api/v1/crawl/${currentJobId}/results`);
    const { internal, external } = await response.json();

    // Display internal links
    const internalContainer = document.getElementById('internal-links');
    internal.slice(0, RESULTS_LIMIT).forEach((url) => {
      const div = document.createElement('div');
      div.className = 'url-item';
      div.textContent = url;
      internalContainer.appendChild(div);
    });

    // Display external links
    const externalContainer = document.getElementById('external-links');
    external.slice(0, RESULTS_LIMIT).forEach((url) => {
      const div = document.createElement('div');
      div.className = 'url-item external';
      div.textContent = url;
      externalContainer.appendChild(div);
    });

    // Update counts
    document.getElementById('internal-count').textContent = internal.length;
    document.getElementById('external-count').textContent = external.length;

    // Show results
    document.getElementById('results-container').style.display = 'grid';
  } catch (error) {
    console.error('Failed to fetch results:', error);
  }
}

// Abort current crawl
async function abortCrawl() {
  if (!currentJobId) return;

  try {
    await fetch(`/api/v1/crawl/${currentJobId}/abort`, { method: 'POST' });
    document.getElementById('status-text').textContent = 'Aborting...';
  } catch (error) {
    console.error('Abort failed:', error);
  }
}

// Initialize
document.getElementById('crawl-url').addEventListener('keypress', (e) => {
  if (e.key === 'Enter') startCrawl();
});
