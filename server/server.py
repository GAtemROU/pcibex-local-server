from quart import Quart 
import sys
from flask_cors import CORS
from quart_bcrypt import Bcrypt
from experiments import experiments_routes
from pcibex import pcibex_routes
from users import users_routes
import server_conf
import os
from db import ping_db
from quart_cors import cors

app = cors(Quart(__name__), allow_origin="*")  # Wrap app directly
app.register_blueprint(experiments_routes, url_prefix='/api/experiments')
app.register_blueprint(pcibex_routes)
app.register_blueprint(users_routes, url_prefix='/api/users')
bcrypt = Bcrypt(app)
app.extensions['bcrypt'] = bcrypt


@app.after_request
def after_request(response):
  response.headers["Access-Control-Allow-Origin"] = "*" # <- You can change "*" for a domain for example "http://localhost"
  response.headers["Access-Control-Allow-Credentials"] = "true"
  response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS, PUT, DELETE"
  response.headers["Access-Control-Allow-Headers"] = "Accept, Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, X-Requested-With"
  return response


@app.before_serving
async def startup():
    # This runs before the app starts serving requests
    await ping_db()
    
if __name__ == "__main__":
  app.run(port=server_conf.PORT, debug=True)
