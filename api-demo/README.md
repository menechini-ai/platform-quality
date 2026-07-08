# ObservAI — Datadog API Demo Lab

Laboratory toolkit for testing Datadog APIs: logs, metrics, events,
incidents, monitors, synthetics, error tracking.

## Setup

```bash
export DATADOG_API_KEY="your_api_key"
export DATADOG_APP_KEY="your_app_key"    # opcional (precisa pra incidents/monitors/synthetics)
export DATADOG_SITE="us5.datadoghq.com"  # opcional
```

Dependências: `httpx` (já no projeto ObservAI).

## Usage

```bash
# Run everything at once (logs + metrics + events, 10 iter)
uv run python api-demo/run.py

# Run a specific scenario
uv run python api-demo/run.py --scenario logs
uv run python api-demo/run.py --scenario metrics
uv run python api-demo/run.py --scenario incidents
uv run python api-demo/run.py --scenario synthetics
uv run python api-demo/run.py --scenario error_tracking

# Scenario sub-commands
uv run python api-demo/run.py --scenario logs load        # burst load
uv run python api-demo/run.py --scenario logs error-wave  # error wave
uv run python api-demo/run.py --scenario metrics spike     # traffic spike
uv run python api-demo/run.py --scenario metrics load      # load sim

# Every scenario once
uv run python api-demo/run.py --all

# Custom iterations
uv run python api-demo/run.py --iter 5 --delay 1
uv run python api-demo/run.py --all
```

## Structure

```
api-demo/
├── run.py              # CLI runner
├── client.py           # DdClient — httpx wrapper for all endpoints
├── data/               # Payload fixtures (JSON samples)
├── scenarios/
│   ├── logs.py         # Log bursts, error waves
│   ├── metrics.py      # Load simulation, spike test
│   ├── incidents.py    # Incident + monitor lifecycle
│   ├── synthetics.py   # API test creation
│   └── error_tracking.py  # Error type simulation
└── README.md
```

## Scenarios

| Scenario | Sub-command | What it sends |
|---|---|---|
| `logs` | `load` | 50 logs, realistic traffic mix (p95, timeouts, degraded) |
| `logs` | `error-wave` | Gradual error rise 5%→80%→10% over 30s |
| `metrics` | `load` | Ramp-up → peak → plateau → cool-down, 65 points |
| `metrics` | `spike` | 1500 RPS spike for 5 datapoints |
| `incidents` | (default) | Create incident + error logs + latency metrics + event |
| `synthetics` | (default) | Create API HTTP test |
| `error_tracking` | (default) | 20 random exceptions (ValueError, TimeoutError, etc.) |
