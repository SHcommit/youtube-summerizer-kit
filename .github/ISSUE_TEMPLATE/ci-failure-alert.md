---
name: CI Failure Alert
about: Automatic issue filed when CI scheduled health check fails
title: "[CI Alert] AI Runtime Harness test failed"
labels: bug, automated-issue
---

## CI Automated Health Check Failure

The automated scheduled CI workflow detected a failure during runtime harness testing.

- **Trigger Event**: `${{ github.event_name }}`
- **Branch/Commit**: `${{ github.sha }}`
- **Workflow Run**: `${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}`

### Details
Please check the workflow run logs to verify if a vendor AI CLI command or dependency updated with breaking changes.
