from quart import Quart, jsonify
from quart_bcrypt import Bcrypt
from quart_cors import cors
from . import server_conf
from .db import get_db_instance, ping_db, create_admin_if_not_exists, close_db_instance
from .experiments import experiments_routes
from .pcibex import pcibex_routes
from .users import users_routes

app = Quart(__name__)
if server_conf.CORS_ALLOWED_ORIGINS:
    app = cors(
        app,
        allow_origin=list(server_conf.CORS_ALLOWED_ORIGINS),
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "Authorization"],
        allow_credentials=True,
    )
app.register_blueprint(experiments_routes, url_prefix='/api/experiments')
app.register_blueprint(pcibex_routes)
app.register_blueprint(users_routes, url_prefix='/api/users')
bcrypt = Bcrypt(app)
app.extensions['bcrypt'] = bcrypt


@app.get("/healthz")
async def healthz():
    try:
        await ping_db()
    except Exception:
        return jsonify({"status": "unavailable"}), 503
    return jsonify({"status": "ok"}), 200


@app.before_serving
async def startup():
    if not server_conf.JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY must be configured")
    client = get_db_instance()
    await ping_db()
    await create_admin_if_not_exists(client)


@app.after_serving
async def shutdown():
    await close_db_instance()
if __name__ == "__main__":
  app.run(port=server_conf.PORT, debug=True)
