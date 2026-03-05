"""Flask Blueprint for /api/modules REST endpoints.

Usage in app2.py:
    modules_bp = create_modules_blueprint(limiter, sanitize_input)
    app.register_blueprint(modules_bp)
"""

from flask import Blueprint, request, jsonify

from agent.crud import get_module, list_modules, list_category, add_module, update_module, delete_module


def create_modules_blueprint(limiter, sanitize_input):
    """Factory that returns a configured Blueprint (avoids circular imports)."""
    bp = Blueprint("modules", __name__)

    @bp.route("/api/modules", methods=["GET"])
    @limiter.limit("30 per minute")
    def api_list_modules():
        """List all modules"""
        return jsonify(list_modules())

    @bp.route("/api/modules/category/<path:prefix>", methods=["GET"])
    @limiter.limit("30 per minute")
    def api_list_category(prefix):
        """List entries by code prefix"""
        return jsonify(list_category(sanitize_input(prefix)))

    @bp.route("/api/modules/<path:module_name>", methods=["GET"])
    @limiter.limit("30 per minute")
    def api_get_module(module_name):
        """Get a specific module"""
        result = get_module(sanitize_input(module_name))
        if not result["found"]:
            return jsonify(result), 404
        return jsonify(result)

    @bp.route("/api/modules", methods=["POST"])
    @limiter.limit("10 per hour")
    def api_add_module():
        """Add a new module"""
        data = request.get_json()
        if not data or not data.get("module_name") or not data.get("code"):
            return jsonify({"error": "module_name and code are required"}), 400
        result = add_module(
            sanitize_input(data["module_name"]),
            sanitize_input(data["code"]),
            sanitize_input(data.get("description", "")),
        )
        if not result["success"]:
            return jsonify(result), 409
        return jsonify(result), 201

    @bp.route("/api/modules/<path:module_name>", methods=["PUT"])
    @limiter.limit("10 per hour")
    def api_update_module(module_name):
        """Update a module — requires ?confirm=true query param."""
        if not request.args.get("confirm"):
            data = request.get_json() or {}
            return jsonify({
                "error": "Confirmation required for destructive operation",
                "pending_action": {
                    "type": "update_module",
                    "params": {
                        "module_name": sanitize_input(module_name),
                        **{k: sanitize_input(v) for k, v in data.items() if isinstance(v, str)},
                    },
                },
            }), 409
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON payload required"}), 400
        result = update_module(
            sanitize_input(module_name),
            new_code=sanitize_input(data["new_code"]) if data.get("new_code") else None,
            new_description=sanitize_input(data["new_description"])
            if data.get("new_description")
            else None,
        )
        if not result["success"]:
            return jsonify(result), 404
        return jsonify(result)

    @bp.route("/api/modules/<path:module_name>", methods=["DELETE"])
    @limiter.limit("10 per hour")
    def api_delete_module(module_name):
        """Delete a module — requires ?confirm=true query param."""
        if not request.args.get("confirm"):
            return jsonify({
                "error": "Confirmation required for destructive operation",
                "pending_action": {
                    "type": "delete_module",
                    "params": {"module_name": sanitize_input(module_name)},
                },
            }), 409
        result = delete_module(sanitize_input(module_name))
        if not result["success"]:
            return jsonify(result), 404
        return jsonify(result)

    return bp
