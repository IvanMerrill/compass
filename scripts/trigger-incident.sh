#!/usr/bin/env bash
# COMPASS Demo Incident Trigger
#
# Usage:
#   ./scripts/trigger-incident.sh missing_index      # Full table scan
#   ./scripts/trigger-incident.sh lock_contention    # Row lock contention
#   ./scripts/trigger-incident.sh pool_exhaustion    # Connection pool exhaustion
#   ./scripts/trigger-incident.sh normal             # Return to normal operation

set -e

INCIDENT_TYPE="${1:-missing_index}"
SAMPLE_APP_URL="http://localhost:8000"

echo "🎯 Triggering incident: $INCIDENT_TYPE"

# Trigger incident mode
response=$(curl -s -X POST "$SAMPLE_APP_URL/trigger-incident" \
  -H "Content-Type: application/json" \
  -d "{\"incident_type\": \"$INCIDENT_TYPE\"}")

echo "✅ Incident mode activated: $(echo "$response" | grep -o '"incident_mode":"[^"]*"')"

if [ "$INCIDENT_TYPE" != "normal" ]; then
  echo ""
  echo "📊 Generating traffic to observe incident..."

  # Generate 20 payment requests to observe incident behavior
  for i in {1..20}; do
    echo -n "."
    curl -s -X POST "$SAMPLE_APP_URL/payment" \
      -H "Content-Type: application/json" \
      -d '{"amount": 100}' > /dev/null
  done

  echo ""
  echo ""
  echo "✅ Traffic generated (20 requests)"
  echo ""
  echo "🔍 Next steps:"
  echo "  1. Wait ~30 seconds for metrics to be scraped"
  echo "  2. View metrics in Grafana: http://localhost:3000"
  echo "  3. Run investigation:"
  echo ""
  echo "     poetry run compass investigate \\"
  echo "       --service payment-service \\"
  echo "       --symptom \"slow database queries and high latency\" \\"
  echo "       --severity high"
  echo ""
  echo "  4. Return to normal: ./scripts/trigger-incident.sh normal"
else
  echo ""
  echo "✅ System returned to normal operation"
fi
