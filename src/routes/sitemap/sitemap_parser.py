from flask import Blueprint, request, jsonify
import requests
from bs4 import BeautifulSoup

sitemap_parser_bp = Blueprint("sitemap_parser", __name__)


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
        urls = parse_sitemap_index(sitemap_url)
        return jsonify({"success": True, "urls": urls, "count": len(urls)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
