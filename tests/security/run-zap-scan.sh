#!/bin/bash
#
# Run OWASP ZAP baseline scan against API Gateway
#
# Usage:
#   ./run-zap-scan.sh [target_url]
#

set -e

TARGET_URL="${1:-http://localhost:8000}"

echo "🔒 Running OWASP ZAP Baseline Scan"
echo "Target: $TARGET_URL"
echo ""

# Create reports directory
mkdir -p reports

# Run ZAP baseline scan in Docker
docker run --rm \
  --network host \
  -v $(pwd):/zap/wrk:rw \
  -t owasp/zap2docker-stable zap-baseline.py \
  -t "$TARGET_URL" \
  -c zap-baseline.conf \
  -r reports/zap-baseline-report.html \
  -J reports/zap-baseline-report.json \
  -m 5 \
  -d

echo ""
echo "✅ ZAP scan completed!"
echo "📄 Report: reports/zap-baseline-report.html"
echo "📊 JSON: reports/zap-baseline-report.json"

