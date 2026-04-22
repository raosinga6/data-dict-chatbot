#!/bin/bash
set -e
pip install uv
uv pip install --system -r backend/requirements.txt
cd backend
pytest tests/ --tb=short -x -k "not (tables or columns or joins)"