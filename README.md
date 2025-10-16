# Studio Round Time Monitor

An independent time monitoring module for tracking time intervals of various components in the SDP gaming system, including TableAPI call times, Roulette device operation times, and Sicbo device operation times.

## Features

- **Non-intrusive Monitoring**: Collects time data through event publish/subscribe system without interfering with main game logic
- **Multi-game Support**: Supports time monitoring for Roulette (Speed/VIP) and Sicbo games
- **Comprehensive Coverage**: Monitors TableAPI calls, device state changes, and MQTT message timing
- **Data Persistence**: Supports JSON, CSV, and database storage
- **Real-time Analysis**: Provides time interval statistics and anomaly detection

## Monitoring Metrics

### TableAPI Time Intervals
- `start-to-betStop`: Time from betting start to betting stop
- `betStop-to-deal`: Time from betting stop to dealing
- `deal-to-finish`: Time from dealing to finish
- `finish-to-start`: Time from finish to next round start

### Roulette Device Time Intervals
- `*X;2-to-*X;3`: Time from ball launch to ball landing
- `*X;3-to-*X;4`: Time from ball landing to detection
- `*X;4-to-*X;5`: Time from detection to result announcement
- `*X;5-to-*X;2`: Time from result announcement to next round start

### Sicbo Device Time Intervals

#### Shaker Device
- `shakerStop-to-shakerShake`: Time from shaker stop to shake start
- `shakerShake-to-shakerStop`: Time from shake start to shaker stop

#### IDP Device  
- `sendDetect-to-receiveResult`: Time from sending detection command to receiving result
- `receiveResult-to-sendDetect`: Time from receiving result to next detection send

## Installation

```bash
cd studio-roundtime-monitor
pip install -r requirements.txt
```

## Usage

### 1. Run as Standalone Service

```bash
python -m studio_roundtime_monitor.main --config config/monitor_config.yaml
```

### 2. Integrate into Existing Game Modules

```python
from studio_roundtime_monitor import TimeMonitor

# Initialize monitor
monitor = TimeMonitor(config)

# Publish events in main game module
monitor.publish_event('tableapi_start', {'table': 'PRD', 'round_id': '123'})
monitor.publish_event('tableapi_betstop', {'table': 'PRD', 'round_id': '123'})
```

## Configuration

The monitor supports configuration through YAML configuration file:

### Local Storage Configuration
```yaml
# config/monitor_config.yaml
monitor:
  enabled: true
  game_types: ['roulette', 'sicbo']
  
storage:
  type: 'json'  # json, csv, database
  path: './data/time_intervals.json'
  
events:
  tableapi:
    enabled: true
    topics: ['tableapi_start', 'tableapi_betstop', 'tableapi_deal', 'tableapi_finish']
  roulette:
    enabled: true
    topics: ['roulette_x2', 'roulette_x3', 'roulette_x4', 'roulette_x5']
  sicbo:
    enabled: true
    topics: ['sicbo_shaker_start', 'sicbo_shaker_stop', 'sicbo_idp_send', 'sicbo_idp_receive']
```

### Telemetry Integration Configuration
```yaml
# config/telemetry_config.yaml
storage:
  type: 'telemetry'  # Send data to remote telemetry servers
  
  telemetry:
    # Loki server for log data
    loki:
      enabled: true
      url: "http://100.64.0.113:3100"  # GE server
      instance_id: "studio-roundtime-monitor"
    
    # Prometheus Pushgateway for metrics
    prometheus:
      enabled: true
      url: "http://100.64.0.113:9091"  # GE server
      job_name: "studio-roundtime-monitor"
    
    # Data routing configuration
    routing:
      time_intervals:
        loki: true      # Send to Loki for logs
        prometheus: true # Send to Prometheus for metrics
      errors:
        loki: true      # Errors go to Loki only
        prometheus: false
```

## Output Format

### JSON Format
```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "game_type": "roulette",
  "table": "PRD", 
  "round_id": "12345",
  "intervals": {
    "start-to-betstop": 15.2,
    "betstop-to-deal": 3.1,
    "deal-to-finish": 1.8,
    "finish-to-start": 2.5
  }
}
```

### CSV Format
```csv
timestamp,game_type,table,round_id,interval_type,duration
2024-01-15T10:30:45.123456,roulette,PRD,12345,start-to-betstop,15.2
2024-01-15T10:31:00.223456,roulette,PRD,12345,betstop-to-deal,3.1
```

## Architecture Design

```
studio-roundtime-monitor/
├── studio_roundtime_monitor/
│   ├── __init__.py
│   ├── core/
│   │   ├── event_system.py      # Event publish/subscribe system
│   │   ├── time_monitor.py      # Main monitor class
│   │   └── interval_calculator.py # Time interval calculator
│   ├── monitors/
│   │   ├── tableapi_monitor.py  # TableAPI monitor
│   │   ├── roulette_monitor.py  # Roulette device monitor
│   │   └── sicbo_monitor.py     # Sicbo device monitor
│   ├── storage/
│   │   ├── json_storage.py      # JSON storage
│   │   ├── csv_storage.py       # CSV storage
│   │   └── database_storage.py  # Database storage
│   └── utils/
│       ├── config.py            # Configuration management
│       └── logger.py            # Logging management
├── config/
│   └── monitor_config.yaml      # Configuration file
├── examples/
│   ├── roulette_integration.py  # Roulette integration example
│   └── sicbo_integration.py     # Sicbo integration example
└── tests/
    ├── test_monitors.py
    └── test_storage.py
```

## Telemetry Integration

The Studio Round Time Monitor can integrate with remote telemetry infrastructure to send monitoring data to centralized logging and metrics systems.

### Features

- **Loki Integration**: Send detailed time interval logs to Loki for centralized logging
- **Prometheus Integration**: Send metrics to Prometheus via Pushgateway for monitoring and alerting
- **Data Routing**: Configure which data types go to which services
- **Server Support**: Compatible with GE (100.64.0.113) and TPE (100.64.0.160) telemetry servers
- **Automatic Metrics**: Generates counter and gauge metrics automatically

### Quick Start with Telemetry

1. **Configure telemetry storage**:
```bash
cp config/telemetry_config.yaml config/monitor_config.yaml
```

2. **Test the integration**:
```bash
python test_telemetry_integration.py
```

3. **Run with telemetry**:
```bash
python -m studio_roundtime_monitor.main --config config/telemetry_config.yaml
```

### Data Types and Routing

| Data Type | Loki | Prometheus | Description |
|-----------|------|------------|-------------|
| Time Intervals | ✅ | ✅ | Detailed logs + metrics |
| Errors | ✅ | ❌ | Error logs only |
| Counters | ❌ | ✅ | Performance counters |
| Gauges | ❌ | ✅ | Current values |

### Monitoring and Visualization

- **Loki Logs**: Query with `{job="studio-roundtime-monitor"}`
- **Prometheus Metrics**: Query `time_interval_duration`, `intervals_processed_total`
- **Grafana Dashboards**: Pre-configured dashboards available
- **Alerting**: Configure alerts based on metrics thresholds

## Integration Guide

### Integration in main_speed.py

```python
# Import at the beginning of file
from studio_roundtime_monitor import TimeMonitor

# Initialize in main() function
monitor = TimeMonitor(config)

# Publish events at key time points
monitor.publish_event('tableapi_start', {
    'table': table['name'], 
    'round_id': round_id
})
```

### Integration in main_sicbo.py

```python
# Initialize monitor in SDPGame class
self.time_monitor = TimeMonitor(config)

# Publish events after key operations
await self.time_monitor.publish_event('sicbo_shaker_start', {
    'round_id': round_id
})
```

## Development Status

- [x] Architecture Design
- [x] Event System
- [ ] TableAPI Monitor
- [ ] Roulette Monitor  
- [ ] Sicbo Monitor
- [ ] Data Storage
- [ ] Integration Guide
