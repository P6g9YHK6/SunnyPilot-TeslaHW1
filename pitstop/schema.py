from opendbc.can.dbc import DBC


def generate_openapi_schema(host: str = "localhost", port: int = 80, dbc=None) -> dict:
  base_url = f"http://{host}" if port == 80 else f"http://{host}:{port}"
  schema = {
    "openapi": "3.0.3",
    "info": {
      "title": "openpilot PitStop API",
      "description": "Unified HTTP API for openpilot: device info, params, settings, backup, model management, and CAN signals.",
      "version": "1.0.0",
    },
    "servers": [{"url": base_url}],
    "tags": [
      {"name": "system", "description": "Device and service status"},
      {"name": "params", "description": "Raw parameter read/write"},
      {"name": "settings", "description": "Settings schema and capabilities"},
      {"name": "backup", "description": "Param backup and restore"},
      {"name": "models", "description": "Model download and management"},
      {"name": "signals", "description": "DBC-decoded CAN signal sending"},
      {"name": "can", "description": "Raw CAN frame sending"},
    ],
    "paths": {
      "/api/status": {
        "get": {
          "tags": ["system"],
          "summary": "Service and car status",
          "responses": {
            "200": {
              "description": "Status",
              "content": {"application/json": {"schema": {
                "type": "object",
                "properties": {
                  "enabled": {"type": "boolean"},
                  "is_offroad": {"type": "boolean"},
                  "is_metric": {"type": "boolean"},
                  "version": {"type": "integer"},
                },
              }}},
            }
          },
        }
      },
      "/api/device": {
        "get": {
          "tags": ["system"],
          "summary": "Device information",
          "responses": {
            "200": {
              "description": "Device info",
              "content": {"application/json": {"schema": {
                "type": "object",
                "properties": {
                  "dongle_id": {"type": "string"},
                  "hardware_serial": {"type": "string"},
                  "version": {"type": "string"},
                  "branch": {"type": "string"},
                  "git_commit": {"type": "string"},
                  "git_commit_date": {"type": "string"},
                  "is_dirty": {"type": "boolean"},
                },
              }}},
            }
          },
        }
      },
      "/api/params": {
        "get": {
          "tags": ["params"],
          "summary": "List all known params with metadata",
          "responses": {"200": {"description": "Param metadata map"}},
        }
      },
      "/api/params/{key}": {
        "get": {
          "tags": ["params"],
          "summary": "Get a param value",
          "parameters": [{"name": "key", "in": "path", "required": True, "schema": {"type": "string"}}],
          "responses": {
            "200": {"description": "Param value"},
            "404": {"description": "Param not found"},
          },
        },
        "post": {
          "tags": ["params"],
          "summary": "Set a param value (string)",
          "parameters": [{"name": "key", "in": "path", "required": True, "schema": {"type": "string"}}],
          "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": {
              "type": "object",
              "properties": {"value": {"type": "string"}},
              "required": ["value"],
            }}},
          },
          "responses": {"200": {"description": "OK"}, "400": {"description": "Bad request"}},
        },
      },
      "/api/params/{key}/bool": {
        "put": {
          "tags": ["params"],
          "summary": "Set a boolean param",
          "parameters": [{"name": "key", "in": "path", "required": True, "schema": {"type": "string"}}],
          "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": {
              "type": "object",
              "properties": {"value": {"type": "boolean"}},
              "required": ["value"],
            }}},
          },
          "responses": {"200": {"description": "OK"}, "400": {"description": "Bad request"}},
        }
      },
      "/api/params/{key}/int": {
        "put": {
          "tags": ["params"],
          "summary": "Set an integer param",
          "parameters": [{"name": "key", "in": "path", "required": True, "schema": {"type": "string"}}],
          "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": {
              "type": "object",
              "properties": {"value": {"type": "integer"}},
              "required": ["value"],
            }}},
          },
          "responses": {"200": {"description": "OK"}, "400": {"description": "Bad request"}},
        }
      },
      "/api/params/{key}/float": {
        "put": {
          "tags": ["params"],
          "summary": "Set a float param",
          "parameters": [{"name": "key", "in": "path", "required": True, "schema": {"type": "string"}}],
          "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": {
              "type": "object",
              "properties": {"value": {"type": "number"}},
              "required": ["value"],
            }}},
          },
          "responses": {"200": {"description": "OK"}, "400": {"description": "Bad request"}},
        }
      },
      "/api/settings/schema": {
        "get": {
          "tags": ["settings"],
          "summary": "Settings UI schema (panels, sections, items, rules)",
          "responses": {"200": {"description": "Settings schema"}, "404": {"description": "Schema not found"}},
        }
      },
      "/api/capabilities": {
        "get": {
          "tags": ["settings"],
          "summary": "Car capabilities (brand, longitudinal, steer type, etc.)",
          "responses": {"200": {"description": "Capabilities object"}},
        }
      },
      "/api/backup": {
        "get": {
          "tags": ["backup"],
          "summary": "List available backups",
          "responses": {"200": {"description": "List of backup files"}},
        }
      },
      "/api/backup/create": {
        "post": {
          "tags": ["backup"],
          "summary": "Create a new param backup",
          "responses": {"200": {"description": "Backup created"}},
        }
      },
      "/api/backup/restore": {
        "post": {
          "tags": ["backup"],
          "summary": "Restore params from a backup file",
          "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": {
              "type": "object",
              "properties": {"name": {"type": "string"}},
              "required": ["name"],
            }}},
          },
          "responses": {"200": {"description": "Restored"}, "400": {"description": "Bad request"}, "404": {"description": "Backup not found"}},
        }
      },
      "/api/models": {
        "get": {
          "tags": ["models"],
          "summary": "List available model bundles",
          "responses": {"200": {"description": "List of bundles"}},
        }
      },
      "/api/models/active": {
        "get": {
          "tags": ["models"],
          "summary": "Get the active model bundle",
          "responses": {"200": {"description": "Active bundle"}},
        }
      },
      "/api/models/select": {
        "post": {
          "tags": ["models"],
          "summary": "Trigger download of a model by index",
          "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": {
              "type": "object",
              "properties": {"index": {"type": "integer"}},
              "required": ["index"],
            }}},
          },
          "responses": {"200": {"description": "OK"}},
        }
      },
      "/api/models/select/default": {
        "post": {
          "tags": ["models"],
          "summary": "Switch to the default built-in model",
          "responses": {"200": {"description": "OK"}},
        }
      },
      "/api/models/progress": {
        "get": {
          "tags": ["models"],
          "summary": "Get current download progress",
          "responses": {"200": {"description": "Progress info"}},
        }
      },
      "/api/models/cancel": {
        "post": {
          "tags": ["models"],
          "summary": "Cancel active model download",
          "responses": {"200": {"description": "OK"}},
        }
      },
      "/api/models/refresh": {
        "post": {
          "tags": ["models"],
          "summary": "Force refresh of model list",
          "responses": {"200": {"description": "OK"}},
        }
      },
      "/api/models/cache": {
        "delete": {
          "tags": ["models"],
          "summary": "Clear downloaded model cache",
          "responses": {"200": {"description": "OK"}},
        }
      },
      "/api/models/favorites": {
        "get": {
          "tags": ["models"],
          "summary": "Get favorite model refs",
          "responses": {"200": {"description": "List of refs"}},
        },
        "post": {
          "tags": ["models"],
          "summary": "Set favorite model refs",
          "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": {
              "type": "object",
              "properties": {"refs": {"type": "array", "items": {"type": "string"}}},
              "required": ["refs"],
            }}},
          },
          "responses": {"200": {"description": "OK"}},
        },
      },
      "/api/v1/status": {
        "get": {
          "tags": ["can"],
          "summary": "CAN API status and DBC info",
          "responses": {"200": {"description": "Status object"}},
        }
      },
      "/api/v1/signals": {
        "get": {
          "tags": ["signals"],
          "summary": "List all DBC-decoded signals",
          "responses": {"200": {"description": "List of messages and signals"}},
        }
      },
      "/api/v1/signals/batch": {
        "post": {
          "tags": ["signals"],
          "summary": "Send multiple known CAN signals atomically",
          "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "message": {"type": "string"},
                  "bus": {"type": "integer", "default": 0},
                  "values": {"type": "object", "additionalProperties": {"type": "number"}},
                },
                "required": ["message", "values"],
              },
            }}},
          },
          "responses": {"200": {"description": "All messages sent"}, "400": {"description": "Invalid request"}},
        }
      },
      "/api/v1/can/send": {
        "post": {
          "tags": ["can"],
          "summary": "Send a raw CAN frame",
          "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": {
              "type": "object",
              "properties": {
                "address": {"type": "integer"},
                "data": {"type": "string", "description": "Hex-encoded bytes"},
                "bus": {"type": "integer", "default": 0},
              },
              "required": ["address", "data"],
            }}},
          },
          "responses": {"200": {"description": "Frame sent"}, "400": {"description": "Invalid request"}},
        }
      },
      "/api/gps": {
        "get": {
          "tags": ["system"],
          "summary": "GPS location and fix status",
          "responses": {"200": {"description": "GPS data"}},
        }
      },
      "/api/calibration": {
        "get": {
          "tags": ["system"],
          "summary": "Live calibration status (pitch/roll/yaw, percent)",
          "responses": {"200": {"description": "Calibration data"}},
        }
      },
      "/api/network": {
        "get": {
          "tags": ["system"],
          "summary": "Network type, signal strength, metered status",
          "responses": {"200": {"description": "Network info"}},
        }
      },
      "/api/sunnylink": {
        "get": {
          "tags": ["system"],
          "summary": "Sunnylink connection status and registration info",
          "responses": {"200": {"description": "Sunnylink status"}},
        }
      },
      "/api/storage": {
        "get": {
          "tags": ["system"],
          "summary": "Disk usage breakdown per directory",
          "responses": {"200": {"description": "Storage usage"}},
        }
      },
      "/openapi.json": {
        "get": {
          "tags": ["system"],
          "summary": "This OpenAPI specification",
          "responses": {"200": {"description": "OpenAPI spec"}},
        }
      },
    },
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
            "content": {"application/json": {"schema": {
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
            }}},
          },
          "responses": {
            "200": {"description": f"Sent {msg.name}"},
            "400": {"description": "Invalid signal values"},
            "503": {"description": "Car not connected or DBC not loaded"},
          },
        }
      }

  return schema
