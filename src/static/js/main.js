async function parseSitemap() {
  const inputURL = document.getElementById('sitemapUrl').value;
  const resultsDiv = document.getElementById('results');

  resultsDiv.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    Processing sitemap...
                </div>
            `;

  fetch('api/v1/parse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: inputURL }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        let html = `
                        <div class="result-box">
                            <button class="copy-btn" onclick="copyResults()">
                                <span class="material-icons">content_copy</span>
                                Copy
                            </button>
                            <h3>Found ${data.urls.length} URLs:</h3>
                            ${data.urls
                              .map(
                                (url) => `
                                <div class="url-item">${url}</div>
                            `,
                              )
                              .join('')}
                        </div>
                    `;
        resultsDiv.innerHTML = html;
      } else {
        resultsDiv.innerHTML = `<div class="error">Error: ${data.error}</div>`;
      }
    })
    .catch((error) => {
      resultsDiv.innerHTML = `<div class="error">Request failed: ${error}</div>`;
    });
}

async function copyResults() {
  const urls = Array.from(document.querySelectorAll('.url-item'))
    .map((item) => item.textContent)
    .join('\n');

  navigator.clipboard
    .writeText(urls)
    .then(() => alert('URLs copied to clipboard!'))
    .catch((err) => alert('Failed to copy URLs'));
}
