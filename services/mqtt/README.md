# EMQX MQTT Broker Configuration

This directory contains configuration for the EMQX MQTT broker used by Ignition Coffee Lab.

## Architecture

```
Pico W → MQTT (port 1883) → EMQX → Ignition MQTT Engine → Tags
```

## Access

| Endpoint | URL | Purpose |
|----------|-----|---------|
| MQTT TCP | `<host-ip>:1883` | Pico W publishes here |
| MQTT WebSocket | `<host-ip>:8083` | Browser clients |
| Dashboard | `http://mqtt.localtest.me` or `<host-ip>:18083` | Admin UI |

## Default Credentials

- **Dashboard**: admin / icl-mqtt-admin (see `.env`)
- **MQTT**: Anonymous allowed (dev mode)

## Topics

The Pico W publishes to:

```
icl/roast_monitor/pico01/temperature  # Temperature readings (JSON)
icl/roast_monitor/pico01/status       # Device status (JSON)
```

### Temperature Payload

```json
{
  "temperature_c": 150.5,
  "temperature_f": 302.9,
  "timestamp": 1699123456.78,
  "device_id": "pico01",
  "status": "good",
  "is_valid": true
}
```

## Configuring Pico W

Update your Pico's `settings.toml` with your Docker host's IP:

```bash
# Find your host IP
# macOS:
ipconfig getifaddr en0

# Linux:
hostname -I | awk '{print $1}'
```

Then set `MQTT_BROKER` in the Pico's settings.toml.

## ACL Configuration

The `acl.conf` file defines access control rules. Current setup:

| Client | Permissions |
|--------|-------------|
| `icl_roast_monitor_pico_w` | Publish to `icl/roast_monitor/pico01/{temperature,status}` |
| `ignition_mqtt_engine` | Subscribe to `icl/#`, publish to `icl/+/+/commands` |
| All clients | Subscribe to `$SYS/#` (system stats) |

**Dev mode**: The last rule `{allow, all, all, ["#"]}` permits everything. Comment it out and uncomment `{deny, all, all, ["#"]}` for production.

## Production Considerations

For production:

1. **Authentication**: Set `EMQX_ALLOW_ANONYMOUS=false`, configure users via dashboard
2. **ACLs**: Comment out the "allow all" rule in `acl.conf`
3. **TLS**: Enable encrypted connections (port 8883)
