#!/usr/bin/env bash
set -euo pipefail

GT=""
PRED=""
LOG=""

qp-evaluate \
  --gt "$GT" \
  --pred "$PRED" \
  --lambda-ins 1.0 \
  --log "$LOG"
