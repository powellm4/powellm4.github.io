# powellm4.github.io

Personal GitHub Pages site and Tesla charging-amps automation.

## What this does

A scheduled GitHub Action runs hourly and sets the car's charging amps based on
the time of day in America/Los_Angeles:

- 00:00–09:00 → 12 A
- 09:00–24:00 → 10 A

If the car is asleep or not plugged in, Tesla returns an error and the
workflow exits 0 (expected no-op).

## Repository secrets

Set these in repo Settings → Secrets and variables → Actions:

| Name | Source |
| ---- | ------ |
| `TESLA_CLIENT_ID` | developer.tesla.com app credentials |
| `TESLA_CLIENT_SECRET` | developer.tesla.com app credentials |
| `TESLA_REFRESH_TOKEN` | output of `scripts/oauth_helper.py` |
| `TESLA_PRIVATE_KEY` | full PEM contents of the EC P-256 private key |
| `TESLA_VIN` | the car's 17-character VIN |
| `GH_PAT` | fine-grained PAT with `Secrets: Read and write` on this repo (lets the workflow auto-rotate `TESLA_REFRESH_TOKEN`) |

## Re-running OAuth (when the refresh token expires)

```bash
TESLA_CLIENT_ID=... TESLA_CLIENT_SECRET=... python3 scripts/oauth_helper.py
```

Then update the `TESLA_REFRESH_TOKEN` secret with `gh secret set TESLA_REFRESH_TOKEN`.

## Manual trigger

```bash
gh workflow run charge-amps.yml
gh run watch
```
