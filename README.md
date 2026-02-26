# Transit Brain NYC

Transit Brain NYC is a high-performance transit data engine built to ingest, process, and serve New York City Transit (MTA) data. It synchronizes static GTFS schedules with real-time arrivals to provide a unified view of the subway system's current state.

## Quick Start

1.  **Environment Setup**
    ```bash
    uv sync
    cp .env.example .env  # Ensure you configure your DB credentials
    ```

2.  **Spin up Infrastructure**
    ```bash
    docker compose up -d
    ```

3.  **Bootstrap Data**
    ```bash
    uv run gtfs-static-reload-all  # Initial load of static subway data
    ```

4.  **Start Services**
    ```bash
    uv run live-hydrator    # Start the real-time polling engine
    uv run api              # Start the FastAPI server (localhost:8000)
    uv run mcp              # (Optional) Start the Model Context Protocol (MCP) server
    ```

---

## Features

- **Static ETL Engine**: Automated pipeline for downloading and ingesting MTA GTFS datasets into PostgreSQL.
- **Subway Live Hydrator**: Low-latency polling service that parses binary Protobuf feeds and maintains system state in Redis.
- **Transit API**: RESTful interface for querying stops, routes, and real-time trip arrivals.
- **MCP Server**: Integration with the [Model Context Protocol](https://modelcontextprotocol.io) for AI-native transit navigation.
- **Type-Safe Models**: Robust data validation using Pydantic and Protocol Buffers.

## Tech Stack

- **Runtime**: Python 3.13+
- **Package Management**: [uv](https://github.com/astral-sh/uv)
- **Primary Database**: PostgreSQL 16 (Relational schedules)
- **State Store**: Redis 7 (Real-time arrivals)
- **API Framework**: FastAPI / Uvicorn
- **AI Integration**: FastMCP
- **Tooling**: Ruff (Linting/Formatting), Pytest (Testing), Flyway (Migrations)

## Project Structure

```text
├── src/
│   ├── services/
│   │   ├── static_etl/           # GTFS download & DB ingestion logic
│   │   └── subway_live_hydrator/ # Real-time feed polling & Redis updates
│   └── transit_core/
│       ├── api/                  # FastAPI routers and dependencies
│       ├── core/                 # Business logic, repositories & Proto definitions
│       ├── infrastructure/       # Redis and DB client implementations
│       └── mcp/                  # MCP server for AI tool-calling
├── proto_schemas/                # MTA and GTFS-Realtime .proto files
├── sql/                          # Flyway migration scripts
└── tests/                        # Integration and unit test suite
```

## Development

### Testing
We use `testcontainers` to run integration tests against real Postgres and Redis instances.
```bash
uv run pytest
```

### Code Quality
```bash
uv run ruff check .  # Linting
uv run ruff format . # Formatting
```

### Deployment
For production environments, use the provided production Docker configuration and Caddy for reverse proxy:
```bash
docker compose -f docker-compose.yml -f docker-compose-prod.yml up -d
```

### Logging
Logs are structured as JSON and can be found in the `logs/` directory:
- `logs/app.log`: General application and API logs.
- `logs/etl.log`: Static data ingestion logs.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
