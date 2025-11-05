#!/bin/bash
# Demo Script: Agent Templates System
# Shows how to use the new template-based agent creation

set -e

BASE_URL="${1:-http://localhost:8000}"

echo "============================================"
echo "Agent Templates Demo - AgentInterOp POC"
echo "============================================"
echo ""
echo "Base URL: $BASE_URL"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Step 1: List Available Agent Templates${NC}"
echo "---------------------------------------"
echo "GET $BASE_URL/api/agents/templates/list"
echo ""
curl -s "$BASE_URL/api/agents/templates/list" | jq '.'
echo ""
read -p "Press Enter to continue..."
echo ""

echo -e "${BLUE}Step 2: View Diabetes Monitoring Template${NC}"
echo "----------------------------------------"
echo "GET $BASE_URL/api/agents/templates/template_diabetes_monitoring"
echo ""
curl -s "$BASE_URL/api/agents/templates/template_diabetes_monitoring" | jq '{
  id,
  name,
  description,
  domain,
  role,
  constitution: .constitution | {purpose, constraints: .constraints[0:2], capabilities: .capabilities[0:3]},
  plan: .plan | {goals: .goals[0:2], tasks: (.tasks | length)}
}'
echo ""
read -p "Press Enter to continue..."
echo ""

echo -e "${BLUE}Step 3: Create Agent from Template${NC}"
echo "-----------------------------------"
echo "POST $BASE_URL/api/agents/templates/template_diabetes_monitoring/instantiate"
echo ""
RESPONSE=$(curl -s -X POST "$BASE_URL/api/agents/templates/template_diabetes_monitoring/instantiate" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo Hospital Diabetes Monitor",
    "description": "Diabetes monitoring agent for demo purposes"
  }')

echo "$RESPONSE" | jq '.'
AGENT_ID=$(echo "$RESPONSE" | jq -r '.agent.id')
echo ""
echo -e "${GREEN}✓ Agent Created! ID: $AGENT_ID${NC}"
echo ""
read -p "Press Enter to continue..."
echo ""

echo -e "${BLUE}Step 4: View Created Agent${NC}"
echo "-------------------------"
echo "GET $BASE_URL/api/agents/$AGENT_ID"
echo ""
curl -s "$BASE_URL/api/agents/$AGENT_ID" | jq '{
  id: .agent.id,
  name: .agent.name,
  status: .agent.status,
  domain: .agent.domain,
  role: .agent.role,
  created_at: .agent.created_at
}'
echo ""
read -p "Press Enter to continue..."
echo ""

echo -e "${BLUE}Step 5: Get Agent Card (A2A Discovery)${NC}"
echo "--------------------------------------"
echo "GET $BASE_URL/api/agents/$AGENT_ID/card"
echo ""
curl -s "$BASE_URL/api/agents/$AGENT_ID/card" | jq '{
  name,
  role,
  protocolVersion,
  preferredTransport,
  capabilities,
  skills: (.skills | length),
  methods
}'
echo ""
read -p "Press Enter to continue..."
echo ""

echo -e "${BLUE}Step 6: Create Second Agent (Medication Reconciliation)${NC}"
echo "-------------------------------------------------------"
echo "POST $BASE_URL/api/agents/templates/template_medication_reconciliation/instantiate"
echo ""
curl -s -X POST "$BASE_URL/api/agents/templates/template_medication_reconciliation/instantiate" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Med Rec Agent - ICU",
    "description": "Medication reconciliation for ICU admissions"
  }' | jq '{
  agent: {
    id: .agent.id,
    name: .agent.name,
    domain: .agent.domain,
    capabilities: .agent.agent_card.capabilities
  },
  message
}'
echo ""
echo -e "${GREEN}✓ Second agent created!${NC}"
echo ""
read -p "Press Enter to continue..."
echo ""

echo -e "${BLUE}Step 7: List All Agents${NC}"
echo "---------------------"
echo "GET $BASE_URL/api/agents/"
echo ""
curl -s "$BASE_URL/api/agents/" | jq '{
  total,
  agents: .agents | map({id, name, domain, status}) | .[0:5]
}'
echo ""
read -p "Press Enter to continue..."
echo ""

echo -e "${BLUE}Step 8: Create SDOH Screening Agent${NC}"
echo "-----------------------------------"
echo "POST $BASE_URL/api/agents/templates/template_social_determinants/instantiate"
echo ""
curl -s -X POST "$BASE_URL/api/agents/templates/template_social_determinants/instantiate" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Community Health SDOH Screener"
  }' | jq '{
  agent: {
    id: .agent.id,
    name: .agent.name,
    role: .agent.role,
    capabilities: .agent.agent_card.capabilities
  },
  message
}'
echo ""
echo -e "${GREEN}✓ SDOH agent created!${NC}"
echo ""

echo "============================================"
echo -e "${GREEN}Demo Complete!${NC}"
echo "============================================"
echo ""
echo "Summary:"
echo "--------"
echo "✓ Listed 3 agent templates"
echo "✓ Viewed template details"
echo "✓ Created 3 healthcare agents from templates:"
echo "  - Diabetes Monitoring Agent"
echo "  - Medication Reconciliation Agent"
echo "  - SDOH Screening Agent"
echo "✓ Retrieved agent cards for A2A discovery"
echo ""
echo "Next steps:"
echo "- View agents in UI: $BASE_URL/studio"
echo "- View agent management: $BASE_URL/agents"
echo "- Use agents in conversations via A2A protocol"
echo ""
echo "Template files located at: app/data/agent_templates/"
echo "API docs: $BASE_URL/docs"
echo ""
