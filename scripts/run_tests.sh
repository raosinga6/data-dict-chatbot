#!/bin/bash
set -e

pip install -r backend/requirements.txt --quiet

cd backend
python -m pytest tests/ -v \
  --tb=short \
  --junit-xml=/workspace/test-results.xml