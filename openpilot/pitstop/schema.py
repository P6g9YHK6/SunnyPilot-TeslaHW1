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
      "/api/gpu": {
        "get": {
          "tags": ["system"],
          "summary": "On-SoC GPU and chestnut eGPU telemetry",
          "responses": {
            "200": {
              "description": "GPU status",
              "content": {"application/json": {"schema": {
                "type": "object",
                "properties": {
                  "present": {"type": "boolean", "description": "on-SoC (Adreno/kgsl) GPU present"},
                  "model": {"type": "string", "nullable": True, "description": "on-SoC GPU model string (kgsl gpu_model)"},
                  "status": {
                    "type": "object",
                    "properties": {
                      "present": {"type": "boolean"},
                      "active": {"type": "boolean", "nullable": True},
                      "max_mode": {"type": "boolean"},
                      "throttled": {"type": "boolean", "nullable": True, "description": "thermal_pwrlevel-derived signal only - see power.throttling_raw for the separate raw kgsl/throttling signal"},
                      "thermal_pwrlevel": {"type": "integer", "nullable": True},
                    },
                  },
                  "clock": {
                    "type": "object",
                    "properties": {
                      "current_mhz": {"type": "integer", "nullable": True},
                      "min_mhz": {"type": "integer", "nullable": True},
                      "max_mhz": {"type": "integer", "nullable": True},
                      "governor": {"type": "string", "nullable": True},
                    },
                  },
                  "busy_percent": {"type": "integer", "nullable": True},
                  "busy": {"type": "object", "nullable": True, "properties": {"used": {"type": "integer"}, "total": {"type": "integer"}}},
                  "power": {
                    "type": "object",
                    "properties": {
                      "default_pwrlevel": {"type": "integer", "nullable": True},
                      "min_pwrlevel": {"type": "integer", "nullable": True},
                      "max_pwrlevel": {"type": "integer", "nullable": True},
                      "num_pwrlevels": {"type": "integer", "nullable": True},
                      "reset_count": {"type": "integer", "nullable": True},
                      "throttling_raw": {"type": "integer", "nullable": True, "description": "raw kgsl/throttling sysfs value - a distinct signal from status.throttled, not cross-checked against it"},
                    },
                  },
                  "clocks": {"type": "array", "items": {"type": "object", "properties": {"mhz": {"type": "integer"}, "time_ns": {"type": "integer"}, "pct": {"type": "number"}}}},
                  "temps_c": {"type": "array", "items": {"type": "number"}},
                  "thermal_status": {"type": "string", "nullable": True},
                  "chestnut": {
                    "type": "object", "nullable": True,
                    "description": "null if chestnut has never been detected on this device",
                    "properties": {
                      "usb": {"type": "object", "nullable": True, "properties": {
                        "present": {"type": "boolean"}, "speed_mbps": {"type": "integer"}, "slow": {"type": "boolean"},
                        "usb3_lane": {"type": "string"}, "link_error_count": {"type": "integer"}, "product": {"type": "string"},
                      }},
                      "hardware_state": {"type": "string", "description": "see openpilot.common.hardware.usb.ChestnutState"},
                      "hardware_state_label": {"type": "string"},
                      "ready": {"type": "boolean", "description": "hardware_state in CHESTNUT_USABLE_STATES"},
                      "powered": {"type": "boolean", "nullable": True},
                      "pcie_link_up": {"type": "boolean", "nullable": True},
                      "pcie_link_label": {"type": "string"},
                      "loading": {"type": "boolean", "description": "ChestnutLoading param - a fresher/more specific signal than hardware_state for mid-boot"},
                      "model_error": {"type": "boolean", "description": "ChestnutModelError param - the big model failed to load even though hardware was ready"},
                      "valid": {"type": "boolean", "nullable": True, "description": "Event.valid on the last chestnutState sample; null if no sample has ever arrived"},
                      "temp_c": {"type": "number"},
                      "memory_temp_c": {"type": "number"},
                      "temp_level": {"type": "string", "enum": ["ok", "warn", "critical"]},
                      "memory_temp_level": {"type": "string", "enum": ["ok", "warn", "critical"]},
                      "power_draw_w": {"type": "number"},
                      "power_limit_w": {"type": "number"},
                      "gpu_usage_percent": {"type": "integer"},
                      "gpu_clock_mhz": {"type": "integer"},
                      "fan_speed_rpm": {"type": "integer"},
                      "pcie_ltssm": {"type": "integer", "description": "raw LTSSM byte; pcie_link_label is the decoded/human form"},
                      "supply_voltage": {"type": "integer", "description": "mV"},
                      "supply_current": {"type": "integer", "description": "mA"},
                      "supply_fault": {"type": "boolean"},
                      "firmware": {"type": "object", "nullable": True, "description": "present only when a mismatch/flash is in progress or failed; includes last_error when a flash attempt failed"},
                      "alerts": {
                        "type": "array", "nullable": True,
                        "description": "currently-active Offroad_Chestnut* alert text (power/PCIe/USB/overheat/etc.), present only when non-empty",
                        "items": {"type": "object", "properties": {"key": {"type": "string"}, "text": {"type": "string"}, "severity": {"type": "integer"}}},
                      },
                    },
                  },
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
          "responses": {"200": {"description": "List of bundles; a chestnut-sourced bundle that's "
                                                "currently unselectable carries an unavailableReason string"}},
        }
      },
      "/api/models/active": {
        "get": {
          "tags": ["models"],
          "summary": "Get the active model bundle",
          "responses": {"200": {"description": "Active bundle, plus activeSource ('chestnut'/'qcom', from "
                                                "deviceState.chestnutPresent - the same VID/PID-only signal the "
                                                "model manager daemon itself uses), chestnutHardwareState/-Label/"
                                                "-Available when relevant (chestnutAvailable mirrors the same "
                                                "CHESTNUT_USABLE_STATES gate used for per-bundle selectability), "
                                                "and staticProvisioning (outcome of the post-update default-model "
                                                "self-heal, if any)"}},
        }
      },
      "/api/models/{name}": {
        "delete": {
          "tags": ["models"],
          "summary": "Delete a cached model bundle's files",
          "parameters": [{"name": "name", "in": "path", "required": True, "schema": {"type": "string"}}],
          "responses": {"200": {"description": "OK"}, "404": {"description": "Bundle not found"},
                        "409": {"description": "Refused: offroad required, or this bundle is the currently active model"}},
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
          "responses": {"200": {"description": "Progress info, plus activeSource ('chestnut'/'qcom')"}},
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
