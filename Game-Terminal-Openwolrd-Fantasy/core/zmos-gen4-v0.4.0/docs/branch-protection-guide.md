# Branch Protection Guide

This guide defines the required GitHub branch protection settings for Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial".

## Target Branches

Apply these rules to:

- `main` (required)
- `develop` (recommended if branch exists)

## Required Settings

In GitHub: **Repository Settings -> Branches -> Add branch protection rule**

Enable the following options:

1. **Require a pull request before merging**
2. **Require approvals**: minimum **1 reviewer**
3. **Require status checks to pass before merging**
4. **Require branches to be up to date before merging**
5. **Required status check**: `verify-strict`
6. **Disallow force pushes**
7. **Disallow direct pushes** to protected branches

## Recommended Additional Controls

- Require conversation resolution before merge
- Include administrators in branch protection enforcement
- Restrict who can dismiss pull request reviews

## Verification Checklist (Admin)

After saving branch protection rules, verify:

1. Open a test PR targeting `main`.
2. Confirm `verify-strict` appears in required checks.
3. Confirm merge is blocked when `verify-strict` is failing.
4. Confirm direct push to `main` is rejected.

## Incident Note

If a merge appears to bypass strict checks, review:

- branch rule pattern (e.g., `main` vs `*` mismatch)
- required status check name spelling (`verify-strict`)
- repository admin override settings
