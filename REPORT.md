# AgentInterOp Codebase Audit Report

## Executive Summary
This audit identifies duplications, dead code, and structural issues in the AgentInterOp repository. The codebase has evolved organically with multiple entry points, duplicate implementations, and overlapping experimental features that need consolidation.

## 1. Multiple Entry Points (CRITICAL)

### Found Entry Points:
- **main.py** - Flask WSGI app for Replit workflow compatibility
- **simple_main.py** - Simplified Flask app with basic A2A/MCP protocols
- **app/main.py** - FastAPI app (PRIMARY - used by Vercel deployment)
- **start.py** - Flask-SocketIO runner with eventlet
- **start_optimized.py** - Optimized startup script
- **start_server.py** - Another server runner
- **run_fastapi.py** - FastAPI runner script

### Analysis:
- **KEEP**: `app/main.py` - This is the canonical FastAPI app used in production via `api/index.py`
- **DEPRECATE**: `main.py` - Flask WSGI app, can forward to FastAPI with shim
- **REMOVE**: `simple_main.py`, `start.py`, `start_optimized.py`, `start_server.py`, `run_fastapi.py` - These are development artifacts not referenced in deployment

### Risk: LOW
- Vercel deployment only uses `app/main.py` via `api/index.py`
- Other entry points are development artifacts

## 2. Duplicate A2A Handlers

### Found Implementations:
- **app/a2a_router.py** - FastAPI router for A2A endpoints
- **app/protocols/a2a.py** - A2A protocol implementation
- **app/protocols/a2a_bcse.py** - BCSE-specific A2A protocol
- **app/inspector/backend.py** - Inspector's A2A implementation
- **app/banterop_ui/a2a_proxy.py** - Proxy for remote A2A calls

### Analysis:
- **KEEP**: `app/a2a_router.py` - Primary A2A router mounted in FastAPI app
- **KEEP**: `app/protocols/a2a.py` - Core protocol logic
- **CONSOLIDATE**: `app/protocols/a2a_bcse.py` - Merge BCSE-specific logic into scenario system
- **KEEP**: `app/inspector/backend.py` - Specialized for inspector functionality
- **KEEP**: `app/banterop_ui/a2a_proxy.py` - New experimental proxy

### Risk: MEDIUM
- Need to ensure all A2A paths remain functional
- BCSE-specific logic should be in scenarios, not protocols

## 3. Multiple Experimental Packages

### Found Packages:
- **app/experimental/** - First experimental features (Claude client, router)
- **app/experimental_v2/** - Second iteration (autonomy, arbiter, guidelines)
- **app/banterop_ui/** - New Banterop-style UI (current work)

### Analysis:
- **KEEP**: All three as they serve different purposes
- **RENAME**: Consider versioning more clearly in future

### Risk: LOW
- These are isolated experimental features

## 4. Duplicate Scenario Implementations

### Found Scenarios:
- **app/scenarios/bcse.py** - Original BCSE scenario
- **app/scenarios/sc_bcse.py** - Structured BCSE scenario
- **app/protocols/a2a_bcse.py** - BCSE in A2A protocol
- **app/protocols/mcp_bcse.py** - BCSE in MCP protocol
- **app/eligibility/bcse.py** - BCSE eligibility engine

### Analysis:
- **KEEP**: `app/scenarios/sc_bcse.py` - Structured scenario implementation
- **DEPRECATE**: `app/scenarios/bcse.py` - Old implementation
- **REMOVE**: Protocol-specific BCSE files - logic belongs in scenarios
- **KEEP**: `app/eligibility/bcse.py` - Core eligibility logic

### Risk: MEDIUM
- Need to ensure BCSE functionality remains intact

## 5. Test File Organization

### Found Test Files:
**Root Directory (13 files):**
- test_a2a_spec.py
- test_age_detection.py
- test_care_commons.py
- test_conversation_flow.py
- test_debug_flow.py
- test_endpoints.py
- test_inspector_conversation.py
- test_inspector_exact.py
- test_local_inspector.py
- test_mcp_endpoints.py
- test_message_proxy.py
- test_proxy_agent_card.py
- test_scheduling_flow.py

**tests/ Directory (4 files):**
- tests/conftest.py
- tests/test_bcse_evaluator.py
- tests/test_protocols_integration.py
- tests/test_scheduling.py
- tests/test_smoke.py

### Analysis:
- **MOVE**: All root test files to `tests/` directory
- **KEEP**: Existing tests in `tests/` directory
- **ADD**: Proper pytest configuration

### Risk: LOW
- Tests are development artifacts, moving won't break production

## 6. Duplicate Patient Data

### Found Data Files:
- **app/data/patients/001.json** - Patient data
- **app/data/patients/001_missing_mammo.json** - Variant patient data
- **app/demo/patient_001.json** - Demo patient
- **app/demo/patient_bcse.json** - BCSE demo patient

### Analysis:
- **CONSOLIDATE**: Move all to `app/data/patients/`
- **REMOVE**: Duplicate `app/demo/` directory

### Risk: LOW
- Update references in code

## 7. Template Duplication

### Found Templates:
- **templates/index.html** - Root template (orphaned)
- **app/web/templates/** - Primary template directory

### Analysis:
- **REMOVE**: Root `templates/` directory
- **KEEP**: `app/web/templates/` as canonical location

### Risk: LOW
- No references to root templates directory

## 8. Hardcoded Values & Issues

### Found Issues:
- Task IDs hardcoded as "task_1" in multiple places
- Invalid state "streaming" referenced in code
- Agent Card using `endpoints{}` instead of `url` field
- Session secret defaulting to "dev-secret-key" in some files

### Analysis:
- **FIX**: Generate unique task IDs with UUID
- **FIX**: Remove invalid "streaming" state references
- **FIX**: Agent Card to use proper `url` field
- **FIX**: Ensure secure session secret generation

### Risk: MEDIUM
- These could cause bugs in production

## 9. Import-Time Network Calls

### Found Issues:
- No blocking I/O or network calls found at import time
- Configuration properly lazy-loaded

### Risk: NONE
- Code is Vercel/serverless safe

## 10. Dead Code & Unused Files

### Potentially Dead:
- **gunicorn.conf.py** - Gunicorn config (not used in Vercel)
- Multiple test result JSON files (final_test_results.json, mcp_test_results.json)
- **api/hello.py** - Unused API endpoint

### Analysis:
- **KEEP**: `gunicorn.conf.py` - May be used for local development
- **REMOVE**: Test result JSON files
- **REMOVE**: `api/hello.py` - Not referenced

### Risk: LOW

## Consolidation Plan

### Phase 1: Non-Breaking Refactors
1. Create shims for deprecated entry points to forward to FastAPI
2. Consolidate A2A handlers with proper routing
3. Merge BCSE-specific protocol code into scenarios

### Phase 2: File Organization
1. Move all test files to `tests/` directory
2. Consolidate patient data files
3. Remove orphaned template directory

### Phase 3: Code Quality
1. Fix hardcoded values (task IDs, states)
2. Update Agent Card structure
3. Add proper configuration management

### Phase 4: Documentation
1. Update README with current architecture
2. Document deprecated modules with removal dates
3. Add development setup guide

## Recommended Immediate Actions

1. **Create branch**: `feature/repo-cleanup-and-banterop-ui`
2. **Add deprecation notices** to old entry points
3. **Consolidate BCSE implementations** into scenario system
4. **Move test files** to proper directory
5. **Update Agent Card** to use correct schema
6. **Add development tools** (formatters, linters)

## Risk Assessment

- **HIGH RISK**: None identified
- **MEDIUM RISK**: A2A handler consolidation, BCSE scenario merging
- **LOW RISK**: File movements, test reorganization, dead code removal

## Backwards Compatibility Requirements

Must maintain:
- `/api/bridge/demo/a2a` - Primary A2A endpoint
- `/a2a` - Legacy A2A endpoint
- `/.well-known/agent-card.json` - Agent discovery
- All existing API routes used by partners
- Environment variable names (PUBLIC_BASE_URL, ANTHROPIC_API_KEY)