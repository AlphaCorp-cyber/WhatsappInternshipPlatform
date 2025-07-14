from app import app
import routes  # noqa: F401

# This ensures routes are loaded when imported
app.register_error_handler(404, lambda e: ("Page not found", 404))
app.register_error_handler(500, lambda e: ("Internal server error", 500))

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
