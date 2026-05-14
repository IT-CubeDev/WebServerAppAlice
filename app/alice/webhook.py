from flask import Blueprint, current_app, jsonify, request

from app.alice.skill import process_alice_request

bp = Blueprint("alice", __name__, url_prefix="/alice")


@bp.route("/webhook", methods=["POST"])
def webhook():
    secret = current_app.config.get("ALICE_WEBHOOK_SECRET") or ""
    if secret and request.headers.get("X-Alice-Secret") != secret:
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "invalid json"}), 400

    out = process_alice_request(body, dict(current_app.config))
    return jsonify(out)
