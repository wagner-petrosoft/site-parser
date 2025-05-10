from flask import Blueprint, jsonify, Response
from src.database import SessionLocal
from src.models import UrlNode, UrlEdge
import json

graph_bp = Blueprint("graph", __name__)


@graph_bp.route("/graph/<job_id>/data")
def graph_data(job_id):
    db = SessionLocal()

    def generate():
        yield '{"nodes": ['

        # Stream nodes in chunks
        nodes = db.query(UrlNode).filter_by(job_id=job_id)
        first_node = True
        for node in nodes.yield_per(100):  # 100 nodes per chunk
            if not first_node:
                yield ","
            yield json.dumps(
                {
                    "id": node.id,
                    "label": node.url,
                    "external": node.is_external,
                    "in_links": 0,  # Will be updated by edges
                    "out_links": 0,
                    "group": f"{0 if node.is_external else 1}",
                }
            )
            first_node = False

        yield '], "edges": ['

        # Stream edges in chunks
        edges = db.query(UrlEdge).filter_by(job_id=job_id)
        first_edge = True
        for edge in edges.yield_per(200):  # 200 edges per chunk
            if not first_edge:
                yield ","
            yield json.dumps(
                {
                    "from": edge.source_id,
                    "to": edge.target_id,
                    "arrows": "to, from",
                }
            )
            first_edge = False

        yield "]}"

    return Response(generate(), mimetype="application/json")
