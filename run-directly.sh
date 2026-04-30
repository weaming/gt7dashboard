#!/usr/bin/env bash

set -euo pipefail

NETWORK_NAME=gt7-net
PS5_IP="${GT7_PLAYSTATION_IP:-192.168.1.100}"
DATA_DIR="${DL:-$HOME/Downloads}/gt7data"

mkdir -p "$DATA_DIR"

export GT7_DATA_DIR="$DATA_DIR"
export BOKEH_ALLOW_WS_ORIGIN='*'
export GT7_PLAYSTATION_IP="$PS5_IP"
export GT7_ADD_BRAKEPOINTS=true

uv run -m bokeh serve .