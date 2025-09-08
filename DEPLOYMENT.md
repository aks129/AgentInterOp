# Minimal Branching + Deploy Strategy (Single Developer)

## 0) One-Time Setup

### GitHub Branch Protection
1. Go to **GitHub → Settings → Branches**
2. Click **"Add rule"** for `main` branch
3. Configure protection:
   ```
   ✅ Require a pull request before merging
   ✅ Require approvals: 1 (you can approve your own)
   ✅ Dismiss stale reviews when new commits are pushed
   ✅ Require status checks to pass before merging
       ✅ Require branches to be up to date before merging
       ✅ Status checks: "CI" (after setting up GitHub Actions)
   ❌ Require conversation resolution before merging
   ✅ Restrict pushes that create files
   ❌ Allow force pushes  
   ❌ Allow deletions
   ```

### Vercel Deployment Strategy
1. **Turn OFF auto-deploy to Production**:
   - Go to Vercel Dashboard → Project Settings → Git
   - **Production Branch**: Set to `none` or disable auto-deploy
   - **Preview Deployments**: Keep enabled for all branches

2. **Manual Promotion Workflow**:
   - Every branch/PR creates a Preview deployment
   - Test the preview URL: `https://agent-inter-op-<hash>-<your-org>.vercel.app`  
   - Manually promote to Production only when ready

### CI Status Checks (Optional)
Simple GitHub Actions workflow for basic validation.

## 1) Everyday Development Flow

### Core Principle
**Keep `main` always "demo-ready"** - never push broken code directly.

### Development Workflow

1. **Start new feature/fix**:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feat/ui-stepper  # or fix/docs-404, exp/mcp-layout
   ```

2. **Develop and test locally**:
   ```bash
   # Make changes
   git add .
   git commit -m "Add UI stepper component"
   git push origin feat/ui-stepper
   ```

3. **Vercel automatically creates Preview**:
   - URL: `https://agent-inter-op-<hash>-<your-org>.vercel.app`
   - Test all functionality on preview
   - Share preview URL for feedback if needed

4. **Create PR when ready**:
   ```bash
   gh pr create --title "Add UI stepper component" --body "Implements step-by-step navigation for multi-stage workflows"
   ```

5. **Review and merge**:
   - Approve your own PR (GitHub allows this)
   - Status checks must pass (CI)
   - Merge to `main`

6. **Promote to Production**:
   - Go to Vercel Dashboard → Deployments
   - Find your merged deployment  
   - Click **"Promote to Production"**

7. **Cleanup**:
   ```bash
   git checkout main
   git pull origin main
   git branch -d feat/ui-stepper  # delete local branch
   git push origin --delete feat/ui-stepper  # delete remote branch
   ```

## 2) Branch Naming Conventions

### Standard Branches
- `feat/feature-name` - New features
- `fix/bug-description` - Bug fixes  
- `docs/update-readme` - Documentation updates
- `refactor/component-cleanup` - Code refactoring

### Experimental/Risky Work
- `spike/research-topic` - Research spikes, proof of concepts
- `exp/experimental-feature` - Experimental features, major changes
- `proto/prototype-name` - Prototypes, temporary implementations

### Examples
```bash
# Good branch names
feat/agent-card-validation
fix/cors-swagger-docs  
exp/websocket-streaming
spike/claude-integration
docs/deployment-guide
refactor/error-handling

# Avoid
feature-branch  # too generic
fix-bug        # not descriptive
john-changes   # not descriptive
```

## 3) Emergency Hotfixes

For critical production issues:

```bash
git checkout main
git pull origin main  
git checkout -b hotfix/critical-security-patch

# Make minimal fix
git add .
git commit -m "Fix critical security vulnerability"
git push origin hotfix/critical-security-patch

# Fast-track PR
gh pr create --title "HOTFIX: Critical security patch" --body "Fixes security vulnerability in authentication"

# After merge, immediately promote to production
```

## 4) Working with Previews

### Preview URL Structure
```
https://agent-inter-op-<git-hash>-<your-org>.vercel.app
```

### Testing Checklist
- [ ] `/healthz` returns 200
- [ ] `/docs` loads Swagger UI  
- [ ] `/openapi.json` returns valid schema
- [ ] `/.well-known/agent-card.json` is A2A compliant
- [ ] Main application functionality works
- [ ] No console errors in browser dev tools

### Sharing Previews
```bash
# Get preview URL from Vercel or GitHub
echo "Preview: https://agent-inter-op-abc123-yourorg.vercel.app"

# Test specific endpoints
curl -s https://agent-inter-op-abc123-yourorg.vercel.app/healthz
curl -s https://agent-inter-op-abc123-yourorg.vercel.app/.well-known/agent-card.json | jq .
```

## 5) Rollback Strategy

### If Production is broken:

1. **Immediate rollback**:
   - Vercel Dashboard → Deployments → Previous working deployment
   - Click **"Promote to Production"**

2. **Fix forward**:
   ```bash
   git checkout -b hotfix/fix-production-issue
   # Fix the issue
   git push origin hotfix/fix-production-issue
   # PR → merge → promote
   ```

## 6) Tips for Solo Development

### Keep PRs small
- One feature per branch
- Aim for < 500 lines changed per PR
- Use draft PRs for work-in-progress

### Use GitHub CLI
```bash
# Install gh CLI
gh auth login

# Quick PR creation
gh pr create --draft  # work in progress
gh pr ready           # mark ready for review
gh pr merge           # merge when ready
```

### Automation Shortcuts
```bash
# Bash aliases for common workflows
alias new-feat='git checkout main && git pull && git checkout -b feat/'
alias new-fix='git checkout main && git pull && git checkout -b fix/'  
alias cleanup-branches='git branch --merged main | grep -v main | xargs -n 1 git branch -d'
```

This strategy gives you:
- ✅ Safe main branch (never broken)
- ✅ Preview deployments for testing
- ✅ Manual production control
- ✅ Clean git history
- ✅ CI validation
- ✅ Easy rollbacks