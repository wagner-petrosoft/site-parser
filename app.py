from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/parse": {
            "origins": [
                "https://us-assets.i.posthog.com",
                # Add other allowed origins if needed
            ],
            "methods": ["POST"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": False,
        }
    },
)


def parse_sitemap_index(sitemap_index_url):
    response = requests.get(sitemap_index_url)
    soup = BeautifulSoup(response.content, "lxml-xml")
    sitemap_urls = [loc.text for loc in soup.find_all("loc")]

    all_urls = []
    for sitemap_url in sitemap_urls:
        sitemap_response = requests.get(sitemap_url)
        sitemap_soup = BeautifulSoup(sitemap_response.content, "lxml-xml")
        urls = [url_loc.text for url_loc in sitemap_soup.find_all("loc")]
        all_urls.extend(urls)

    return all_urls


@app.route("/", methods=["GET"])
def index():
    return render_template("sitemap-parser.html")


@app.route("/parse", methods=["POST"])
def parse_sitemap():
    data = request.get_json()
    sitemap_url = data.get("url")
    try:
        urls = parse_sitemap_index(sitemap_url)
        return jsonify({"success": True, "urls": urls})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
