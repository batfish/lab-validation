# GitHub Actions Workflows

## ci.yml

The main continuous integration workflow that runs on pull requests and pushes to main/develop branches. It includes:

- Code linting with pre-commit hooks
- Unit tests with coverage reporting
- Lab discovery and parallel integration testing
- Batfish JAR building and caching

## daily-ci.yml

A scheduled workflow that runs the full CI suite daily at 8AM Pacific time. Features:

- Reuses the existing `ci.yml` workflow
- Runs automatically via cron schedule: `0 15 * * *` (8AM Pacific)
- Can be triggered manually via `workflow_dispatch`
- Sends Slack notifications to a configured channel on failure

### Setup Required

To enable Slack notifications, add the following secret to your repository:

- `LAB_VALIDATION_SLACK_WEBHOOK_URL`: Your Slack incoming webhook URL

### Notification Details

The Slack notification includes:

- Workflow name and status
- Trigger type (scheduled vs manual)
- Repository and commit information
- Direct link to the failed workflow run
