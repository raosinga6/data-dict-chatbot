#!/bin/bash
set -e

EXTERNAL_IP=$(kubectl get svc dd-streamlit-svc \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Smoke testing http://$EXTERNAL_IP/health"

curl --fail --retry 5 --retry-delay 5 \
  "http://$EXTERNAL_IP/health" | grep '"status":"healthy"'

echo "Smoke test passed"