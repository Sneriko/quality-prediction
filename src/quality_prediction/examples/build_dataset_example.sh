
---

## `examples/build_dataset_example.sh`
This mirrors your current `__main__` dataset paths.

```bash
#!/usr/bin/env bash
set -euo pipefail

# --- Resources ---
CHAR_LM=""
NGRAM_SETS=""
BIN_CONFIG=""

# --- Output ---
OUT_CSV=""

# --- Datasets ---
GT0=""
PRED0=""

GT1=""
PRED1=""

qp-build-dataset \
  --out-csv "$OUT_CSV" \
  --bin-config "$BIN_CONFIG" \
  --char-lm "$CHAR_LM" \
  --ngram-sets "$NGRAM_SETS" \
  --lambda-ins 1.0 \
  --century 17 \
  --script-type kurrent \
  --dataset ds0 "$GT0" "$PRED0" \
  --dataset ds1 "$GT1" "$PRED1"
