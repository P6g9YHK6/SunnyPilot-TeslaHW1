from opendbc.can.dbc import DBC


def generate_openapi_schema(host: str = "localhost", port: int = 8700, dbc: DBC | None = None) -> dict:
  base_path = f"http://{host}:{port}"
  schema = {
    "openapi": "3.0.3",
    "info": {
      "title": "openpilot CAN API",
      "description": "HTTP API for sending known and raw CAN signals",
      "version": "1.0.0",
    },
    "servers": [{"url": base_path}],
    "paths": {
      "/api/v1/status": {
        "get": {
          "summary": "API and car status",
          "responses": {"200": {"description": "Status object", "content": {"application/json": {}}}},
        }
      },
      "/api/v1/signals": {
        "get": {
          "summary": "List known DBC signals",
          "responses": {"200": {"description": "List of messages and signals", "content": {"application/json": {}}}},
        }
      },
      "/api/v1/signals/batch": {
        "post": {
          "summary": "Send multiple known signals atomically",
          "requestBody": {
            "required": True,
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "message": {"type": "string"},
                      "bus": {"type": "integer", "default": 0},
                      "values": {
                        "type": "object",
                        "additionalProperties": {"type": "number"},
                      },
                    },
                    "required": ["message", "values"],
                  },
                }
              }
            },
          },
          "responses": {
            "200": {"description": "All messages sent"},
            "400": {"description": "Invalid request"},
          },
        }
      },
      "/api/v1/can/send": {
        "post": {
          "summary": "Send raw CAN frame",
          "requestBody": {
            "required": True,
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "address": {"type": "integer"},
                    "data": {"type": "string", "description": "Hex-encoded bytes"},
                    "bus": {"type": "integer", "default": 0},
                  },
                  "required": ["address", "data"],
                }
              }
            },
          },
          "responses": {
            "200": {"description": "Frame sent"},
            "400": {"description": "Invalid request"},
          },
        }
      },
      "/openapi.json": {
        "get": {
          "summary": "OpenAPI specification",
          "responses": {"200": {"description": "OpenAPI spec"}},
        }
      },
    },
    "x-tagGroups": [
      {"name": "Known Signals", "tags": ["signals"]},
      {"name": "Raw CAN", "tags": ["can"]},
      {"name": "System", "tags": ["system"]},
    ],
  }

  if dbc is not None:
    for msg in dbc.msgs.values():
      path = f"/api/v1/signals/{msg.name}"
      sig_props = {}
      for sig in msg.sigs.values():
        sig_type = "number"
        if sig.type != 0 or not sig.is_signed:
          sig_type = "integer"
        sig_props[sig.name] = {
          "type": sig_type,
          "description": f"bit {sig.start_bit}, size {sig.size}, factor {sig.factor}, offset {sig.offset}",
        }
        if sig.factor != 0:
          sig_props[sig.name]["minimum"] = (0 - sig.offset) / sig.factor
          sig_props[sig.name]["maximum"] = ((1 << sig.size) - 1 - sig.offset) / sig.factor if sig.size < 64 else 0

      schema["paths"][path] = {
        "post": {
          "summary": f"Send {msg.name} (0x{msg.address:X})",
          "tags": ["signals"],
          "requestBody": {
            "required": True,
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "bus": {"type": "integer", "default": 0},
                    "values": {
                      "type": "object",
                      "properties": sig_props,
                      "required": [],
                    },
                  },
                  "required": ["values"],
                }
              }
            },
          },
          "responses": {
            "200": {"description": f"Sent {msg.name}"},
            "400": {"description": "Invalid signal values"},
            "503": {"description": "Car not connected or DBC not loaded"},
          },
        }
      }

  return schema
