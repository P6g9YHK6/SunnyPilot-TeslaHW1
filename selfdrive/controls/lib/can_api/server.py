import logging
import os

from aiohttp import web

from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.can_api.handler import CanApiHandler
from openpilot.selfdrive.controls.lib.can_api.schema import generate_openapi_schema

logger = logging.getLogger("can_api")

HOST = "0.0.0.0"
PORT = 8700

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class CanApiServer:
  def __init__(self):
    self.handler = CanApiHandler()
    self.params = Params()
    self._swagger_html = None

  def _load_swagger_html(self) -> str:
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
      with open(index_path) as f:
        return f.read()
    return """<!DOCTYPE html>
<html><head><title>CAN API</title></head>
<body><h1>CAN API</h1>
<p>Swagger UI not bundled.</p>
<pre id="spec"></pre>
<script>fetch('/openapi.json').then(r=>r.json()).then(d=>document.getElementById('spec').textContent=JSON.stringify(d,null,2))</script>
</body></html>"""

  async def handle_status(self, request):
    try:
      dbc_names = self.handler.dbc_names
    except Exception:
      dbc_names = None
    return web.json_response({
      "car": list(dbc_names.keys()) if dbc_names else None,
      "dbc_loaded": self.handler.dbc is not None,
      "api_enabled": self.params.get_bool("CanApiEnabled"),
      "offroad": True,
    })

  async def handle_signals(self, request):
    return web.json_response(self.handler.get_signals())

  async def handle_signal_send(self, request):
    msg_name = request.match_info.get("name")
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON")

    values = body.get("values", {})
    bus = body.get("bus", 0)
    result = self.handler.send_signal(msg_name, values, bus)
    if result is None:
      raise web.HTTPBadRequest(text=f"Unknown message: {msg_name}")
    return web.json_response(result)

  async def handle_batch_send(self, request):
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON")

    if not isinstance(body, list):
      raise web.HTTPBadRequest(text="Expected array of messages")

    results = []
    for item in body:
      msg_name = item.get("message")
      values = item.get("values", {})
      bus = item.get("bus", 0)
      result = self.handler.send_signal(msg_name, values, bus)
      results.append({"message": msg_name, "ok": result is not None})
    return web.json_response(results)

  async def handle_raw_send(self, request):
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON")

    address = body.get("address")
    data_hex = body.get("data")
    bus = body.get("bus", 0)

    if address is None or data_hex is None:
      raise web.HTTPBadRequest(text="Missing address or data")

    try:
      data = bytes.fromhex(data_hex)
    except ValueError:
      raise web.HTTPBadRequest(text="Invalid hex data")

    self.handler.send_raw(int(address), data, int(bus))
    return web.json_response({"address": int(address), "data": data.hex(), "bus": int(bus)})

  async def handle_openapi(self, request):
    schema = generate_openapi_schema(
      host=request.host.split(":")[0] if ":" in request.host else request.host,
      port=int(request.host.split(":")[1]) if ":" in request.host else PORT,
      dbc=self.handler.dbc,
    )
    return web.json_response(schema)

  async def handle_docs(self, request):
    html = self._swagger_html
    if html is None:
      self._swagger_html = self._load_swagger_html()
    return web.Response(text=html, content_type="text/html")

  async def handle_static(self, request):
    filename = request.match_info.get("filename", "")
    filepath = os.path.normpath(os.path.join(STATIC_DIR, filename))
    if not filepath.startswith(STATIC_DIR):
      raise web.HTTPForbidden()
    if os.path.isfile(filepath):
      return web.FileResponse(filepath)
    raise web.HTTPNotFound()

  def build_app(self):
    app = web.Application()
    app.router.add_get("/api/v1/status", self.handle_status)
    app.router.add_get("/api/v1/signals", self.handle_signals)
    app.router.add_post("/api/v1/signals/{name}", self.handle_signal_send)
    app.router.add_post("/api/v1/signals/batch", self.handle_batch_send)
    app.router.add_post("/api/v1/can/send", self.handle_raw_send)
    app.router.add_get("/openapi.json", self.handle_openapi)
    app.router.add_get("/docs", self.handle_docs)
    app.router.add_get("/docs/{filename:.+}", self.handle_static)
    return app


def can_api_thread(host: str = HOST, port: int = PORT):
  logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
  logger.setLevel(logging.INFO)

  server = CanApiServer()
  app = server.build_app()
  logger.info(f"CAN API starting on {host}:{port}")
  web.run_app(app, host=host, port=port)


def main():
  can_api_thread()


if __name__ == "__main__":
  main()
