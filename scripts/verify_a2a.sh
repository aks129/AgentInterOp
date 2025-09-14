#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"

echo "========================================="
echo "A2A Endpoint Verification Script"
echo "Testing: $BASE_URL"
echo "========================================="
echo

echo "== TEST 1: JSON-RPC call (tasks/cancel) =="
echo "Testing standard JSON-RPC without Content-Length requirement..."
curl -i -sS -X POST "$BASE_URL/api/bridge/demo/a2a" \
  -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"tasks/cancel","params":{"id":"x"},"id":3}' | sed -n '1,20p'

echo
echo "== TEST 2: STREAMING call (message/stream) =="
echo "Testing SSE streaming without Content-Length..."
curl -i -sS -N -X POST "$BASE_URL/api/bridge/demo/a2a" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  --data '{"jsonrpc":"2.0","method":"message/stream","params":{"message":{"parts":[{"kind":"text","text":"test"}]}},"id":1}' | sed -n '1,30p'

echo
echo "== TEST 3: Context endpoint JSON =="
echo "Testing context-aware endpoint..."
curl -i -sS -X POST "$BASE_URL/api/bridge/custom/a2a" \
  -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"tasks/get","params":{"id":"test"},"id":5}' | sed -n '1,20p'

echo
echo "== TEST 4: Context endpoint streaming =="
echo "Testing context-aware endpoint with streaming..."
curl -i -sS -N -X POST "$BASE_URL/api/bridge/custom/a2a" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  --data '{"jsonrpc":"2.0","method":"message/stream","params":{},"id":7}' | sed -n '1,30p'

echo
echo "== TEST 5: Empty body handling =="
echo "Testing error handling for empty body..."
curl -i -sS -X POST "$BASE_URL/api/bridge/demo/a2a" \
  -H "Content-Type: application/json" \
  --data '' | sed -n '1,20p'

echo
echo "========================================="
echo "VERIFICATION NOTES:"
echo "- JSON responses may or may not have Content-Length"
echo "- Streaming responses should use Transfer-Encoding: chunked"
echo "- Streaming responses should NOT have Content-Length"
echo "- Look for 'Cache-Control: no-cache' in streaming responses"
echo "========================================="