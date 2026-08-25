#!/usr/bin/env bash
# run_phase1.sh — Run all Phase 1 scripts in order.
# Usage: bash backend/ml/run_phase1.sh
# Expects to be run from the repo root (platemind/).

set -e
VENV="backend/.venv/bin/python3"

echo "╔══════════════════════════════════════════╗"
echo "║  PlateMind — Phase 1: Data & Baselines   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

echo "Step 1/6 — Data cleaning & exploration"
$VENV backend/ml/01_explore.py

echo ""
echo "Step 2/6 — Ingredient normalization"
$VENV backend/ml/02_normalize_ingredients.py

echo ""
echo "Step 3/6 — Load to SQLite DB"
$VENV backend/ml/03_load_db.py

echo ""
echo "Step 4/6 — User feature engineering"
$VENV backend/ml/04_user_features.py

echo ""
echo "Step 5/6 — Baseline model training"
$VENV backend/ml/05_baseline_models.py

echo ""
echo "Step 6/6 — Evaluation"
$VENV backend/ml/06_evaluate.py

echo ""
echo "✅  Phase 1 complete."
echo "    Eval report → backend/ml/eval_report.md"
echo "    Processed data → backend/data/processed/"
echo "    Models → backend/models/"
