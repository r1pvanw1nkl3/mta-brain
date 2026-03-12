#!/bin/bash
set -e

# Change working directory to the project root (parent of the scripts directory)
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "🚀 Starting OSRM Map Deployment Pipeline from $PROJECT_ROOT..."

# 1. Load configuration from .env in the project root
if [ -f "$PROJECT_ROOT/.env" ]; then
  # Export variables from .env ignoring comments
  export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
else
  echo "❌ Error: .env file not found in $PROJECT_ROOT!"
  exit 1
fi

if [ -z "$HETZNER_IP" ]; then
  echo "❌ Error: HETZNER_IP is not set in your .env file."
  echo "Please add it: HETZNER_IP=your_server_ip"
  exit 1
fi

HETZNER_USER=${HETZNER_USER:-root}
PROJECT_DIR_ON_SERVER="~/mta-brain"
OSRM_DATA_DIR="$PROJECT_ROOT/data/osrm"

# Bounding box for NYC + Westchester buffer + NJ shore
# Format: min_lon,min_lat,max_lon,max_lat
BBOX="-74.3,40.45,-73.65,41.1"

MAP_URL="https://download.geofabrik.de/north-america/us/new-york-latest.osm.pbf"
PBF_FILE="new-york-latest.osm.pbf"
OSRM_PREFIX="nyc_buffered_extract"

# Create local data directory
mkdir -p "$OSRM_DATA_DIR"

# 2. Download the full New York state map data
echo "📥 Downloading latest New York map from Geofabrik..."
if [ ! -f "$OSRM_DATA_DIR/$PBF_FILE" ]; then
    curl -o "$OSRM_DATA_DIR/$PBF_FILE" "$MAP_URL"
else
    echo "✅ $PBF_FILE already exists locally. Skipping download."
fi

# 3. Crop the map using osmium inside a lightweight Alpine container
echo "✂️  Cropping map to NYC + Westchester buffer (BBOX: $BBOX)..."
docker run --rm -v "$OSRM_DATA_DIR":/data alpine sh -c "
    apk add --no-cache osmium-tool && \
    osmium extract -b $BBOX /data/$PBF_FILE -o /data/${OSRM_PREFIX}.osm.pbf --overwrite
"
echo "✅ Cropped map successfully to ${OSRM_PREFIX}.osm.pbf."

# 4. Extract and build the routing graph using OSRM Docker locally
echo "🏗️  Building OSRM routing graph (this may take a while and use high CPU/RAM)..."

# Extract
docker run --rm -v "$OSRM_DATA_DIR":/data osrm/osrm-backend:latest osrm-extract -p /opt/car.lua /data/${OSRM_PREFIX}.osm.pbf

# Partition (for Multi-Level Dijkstra - MLD)
docker run --rm -v "$OSRM_DATA_DIR":/data osrm/osrm-backend:latest osrm-partition /data/${OSRM_PREFIX}.osrm

# Customize
docker run --rm -v "$OSRM_DATA_DIR":/data osrm/osrm-backend:latest osrm-customize /data/${OSRM_PREFIX}.osrm

echo "✅ OSRM graph successfully built locally."

# 5. Deploy to Hetzner
echo "🚢 Deploying OSRM data to Hetzner server ($HETZNER_USER@$HETZNER_IP)..."

# Ensure the target directory exists on the server
ssh "${HETZNER_USER}@${HETZNER_IP}" "mkdir -p ${PROJECT_DIR_ON_SERVER}/data/osrm"

# Rsync ONLY the processed OSRM files (exclude massive raw .osm.pbf files)
rsync -avz --progress \
    --include="${OSRM_PREFIX}.*" \
    --exclude="*" \
    "$OSRM_DATA_DIR/" \
    "${HETZNER_USER}@${HETZNER_IP}:${PROJECT_DIR_ON_SERVER}/data/osrm/"

# 6. Restart OSRM container on the server
echo "🔄 Restarting OSRM service on the Hetzner server..."
ssh "${HETZNER_USER}@${HETZNER_IP}" "cd ${PROJECT_DIR_ON_SERVER} && docker compose -f docker-compose.yml -f docker-compose-prod.yml up -d osrm"

echo "🎉 OSRM Map Deployment Pipeline Complete!"
