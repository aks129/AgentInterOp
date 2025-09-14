#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://localhost:8000}"
echo "Testing A2A endpoints at $BASE"
echo "================================"

echo -n "1. Health check: "
curl -s "$BASE/healthz" | jq -r '.status // "OK"' || echo "FAILED"

echo -n "2. Agent Card: "
curl -s "$BASE/.well-known/agent-card.json" | jq -r '.skills[0].discovery.url // .skills[0].url // "No URL found"' || echo "FAILED"

echo "3. A2A message/send test:"
RESPONSE=$(curl -s "$BASE/api/bridge/demo/a2a" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"message/send","params":{"message":{"parts":[{"kind":"text","text":"Hello, this is a smoke test"}]}}}' || echo '{"error":"Request failed"}')
echo "$RESPONSE" | jq '.result // .error // .'

echo "4. A2A tasks/get test:"
RESPONSE=$(curl -s "$BASE/api/bridge/demo/a2a" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tasks/get","params":{}}' || echo '{"error":"Request failed"}')
echo "$RESPONSE" | jq '.result // .error // .'

echo "================================"
echo "Smoke test complete!"