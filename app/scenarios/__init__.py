# Scenario registry package
from app.scenarios.registry import register

# Import and register all scenarios
from app.scenarios import bcse, clinical_trial, referral_specialist, prior_auth, custom

# Register scenarios with the registry
register("bcse", bcse)
register("clinical_trial", clinical_trial)
register("referral_specialist", referral_specialist)
register("prior_auth", prior_auth)
register("custom", custom)