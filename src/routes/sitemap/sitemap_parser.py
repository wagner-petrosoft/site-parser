from flask import Blueprint, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

sitemap_parser_bp = Blueprint("sitemap_parser", __name__)


def get_sitemap_urls(base_url):
    """Fetch all URLs from sitemap.xml or sitemap_index.xml"""
    sitemap_urls = []
    for sitemap_path in ["", "/sitemap.xml", "/sitemap_index.xml"]:
        try:
            response = requests.get(urljoin(base_url, sitemap_path), timeout=5)
            soup = BeautifulSoup(response.content, "lxml-xml")
            if soup.find_all("sitemapindex"):
                # Handle nested sitemaps
                sitemap_urls.extend(
                    parse_sitemap_index(urljoin(base_url, sitemap_path))
                )
            else:
                urls = [loc.text for loc in soup.find_all("loc")]
                if urls:
                    sitemap_urls.extend(urls)
        except Exception:
            continue
    return list(set(sitemap_urls)) if sitemap_urls else [base_url]


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


@sitemap_parser_bp.route("/parse", methods=["POST"])
def parse_sitemap():
    data = request.get_json()
    sitemap_url = data.get("url")

    try:
        urls = get_sitemap_urls(sitemap_url)
        return jsonify({"success": True, "urls": urls, "count": len(urls)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
