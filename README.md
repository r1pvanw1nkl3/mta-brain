# MTA Brain

MTA Brain is a Python-based data engineering project designed to ingest, process, and store New York City Transit (MTA) data. It handles both static GTFS data (schedules, routes, stops) and real-time GTFS feeds (live arrivals, delays).

## Features

- **Static ETL:** Downloads and parses static GTFS feeds into a PostgreSQL database.
- **Live Hydration:** Polls MTA GTFS Realtime feeds and updates a Redis cache with current transit state.
- **Core Library:** Shared logic for database connectivity, configuration, and data models.

## Tech Stack

- **Language:** Python 3.13+
- **Package Manager:** [uv](https://github.com/astral-sh/uv)
- **Database:** PostgreSQL 16 (with Flyway for migrations)
- **Cache/Real-time Store:** Redis 7
- **Data Formats:** Protocol Buffers (GTFS Realtime), CSV (GTFS Static)

## Getting Started

### Prerequisites

- **Python 3.13+** (Managed by `uv` via `.python-version`)
- **uv**: For dependency management.
- **Docker**: For running PostgreSQL and Redis.

### Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   uv sync
   ```

### Configuration

The application uses environment variables for configuration. Create a `.env` file in the root directory based on the following required variables:

```env
ETL_DB_USER=your_etl_user
ETL_DB_PASSWORD=your_etl_password
APP_DB_USER=your_app_user
APP_DB_PASSWORD=your_app_password
DB_NAME=mta_brain
```

See `src/transit_core/config.py` for all available settings.

### Infrastructure Setup

Start PostgreSQL, Redis, and run database migrations using Docker Compose:

```bash
docker compose up -d
```

## Running the Application

### 1. Load Static Data (ETL)
Download and ingest the latest static GTFS data into PostgreSQL:
```bash
uv run reload-all-gtfs
```

### 2. Run Live Data Hydrator
Start the service that polls MTA Realtime feeds and updates Redis:
```bash
uv run live-hydrator
```

## Development

### Running Tests
The project uses `pytest` and `testcontainers` for integration testing.
```bash
uv run pytest
```

### Linting & Formatting
The project uses `ruff` for linting and formatting.
```bash
uv run ruff check .
uv run ruff format .
```

## Project Structure

- `src/transit_core`: Shared core logic, database connections, configuration, and data models.
- `src/services/static_etl`: Logic for downloading and parsing static GTFS zip files.
- `src/services/subway_live_hydrator`: Logic for polling and parsing real-time Protobuf feeds.
- `proto_schemas`: Original `.proto` files for GTFS Realtime and NYCT extensions.
- `sql`: Database migration scripts.
- `tests`: Comprehensive test suite.
