#!/usr/bin/env bash

set -euo pipefail

NETWORK_NAME=gt7-net
PS5_IP="${GT7_PLAYSTATION_IP:-192.168.1.100}"
DATA_DIR="${DL:-$HOME/Downloads}/gt7data"

mkdir -p "$DATA_DIR"

docker rm -f gt7-dashboard >/dev/null 2>&1 || true
docker network rm $NETWORK_NAME >/dev/null 2>&1 || true

docker network create \
    --driver bridge \
    --opt com.docker.network.bridge.enable_ip_masquerade=false \
    "$NETWORK_NAME" >/dev/null

docker run -d --restart unless-stopped \
    --name gt7-dashboard \
    --network "$NETWORK_NAME" \
    -p 5006:5006/tcp \
    -p 33740:33740/udp \
    -v "$DATA_DIR":/usr/src/app/data \
    -e BOKEH_ALLOW_WS_ORIGIN='*' \
    -e GT7_PLAYSTATION_IP="$PS5_IP" \
    -e TZ=Asia/Shanghai \
    -e GT7_ADD_BRAKEPOINTS=true \
    gt7-dashboard
