# Pull Request

## What changed
- [ ] UI change
- [ ] Protocol change (A2A/MCP)
- [ ] Docs/discovery
- [ ] Backend/API
- [ ] Configuration

## Smoke checks (2-minute verification)
- [ ] `/healthz` returns 200
- [ ] `/openapi.json` returns valid schema  
- [ ] `/docs` renders Swagger UI
- [ ] `/.well-known/agent-card.json` is A2A compliant
- [ ] Preview URL tested on Vercel (paste link below)

## Preview URL
<!-- Vercel automatically creates: https://agent-inter-op-<hash>-<org>.vercel.app -->
Preview: _paste vercel preview URL here_

## Screenshots / curl proof
<!-- For UI changes: screenshots -->
<!-- For API changes: curl commands showing before/after -->
<!-- For discovery changes: show agent card diff -->

```bash
# Example verification commands:
curl -s https://your-preview.vercel.app/healthz
curl -s https://your-preview.vercel.app/.well-known/agent-card.json | jq .name
```

## Notes
<!-- Any additional context, concerns, or follow-up tasks -->

---

**Merge checklist:**
- [ ] CI passes (warn-only checks reviewed)
- [ ] Preview deployment works
- [ ] Ready to promote to production after merge