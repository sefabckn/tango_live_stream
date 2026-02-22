#!/bin/bash
set -e

# Generate data and seed DB only if the database doesn't already exist
if [ ! -f "data/platform.db" ]; then
    echo "==> Generating synthetic data..."
    python scripts/data_generator.py

    echo "==> Seeding database..."
    python scripts/seed_database.py
else
    echo "==> Database already exists, skipping generation."
fi

echo "==> Starting Streamlit dashboard..."
exec streamlit run dashboard/dashboard.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true
