# MTA Brain

## How to run MTA Brain

#### Prereqs
- UV
- Docker

#### Running the application

1. Run "docker compose up -d". This handles all the infrastructure, including postgres, flyway & script migrations, and redis.
2. Run "uv run reload-all-gtfs". This loads the MTA's static GTFS (basic and supplemented) into Postgres.
3. Run "uv run live-hydrator". Loads the GTFS Realtime data into Redis at regular intervals.


is 'uv pip install -e .' necessary?? tbd!
