# GitHub setup checklist

1. Add these files to the repository.
2. Replace `@YOUR_GITHUB_HANDLE` in CODEOWNERS.
3. Protect `main`: require PRs, at least one approval where team size permits, required CI/secret-scan checks, stale approval dismissal, conversation resolution; disallow force pushes and deletion.
4. After first successful workflow run, mark exact CI job names as required status checks.
5. Enable Dependabot alerts/security updates where available.
6. Keep Actions permissions read-only by default.
7. No deployment secrets are required for Milestone 0.
8. Later deployment workflows should use separate environments and approval gates.
