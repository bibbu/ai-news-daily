#!/bin/bash
# deploy/trigger_github.sh
# Called by workflow.py after pipeline completes.
# Triggers GitHub Actions repository_dispatch to deploy to GitHub Pages.
#
# Usage: ./trigger_github.sh YYYY-MM-DD
# Environment: GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO
#
# SETUP:
# 1. Set GITHUB_TOKEN in environment (fine-grained PAT with repo + workflow scope)
# 2. Set GITHUB_OWNER (your GitHub username/org)
# 3. Set GITHUB_REPO (default: ai-news-daily)
#
# Example in workflow.py:
#   result = subprocess.run(
#       ['bash', str(DEPLOY_DIR/'trigger_github.sh'), date_str],
#       env={**os.environ, 'GITHUB_TOKEN': os.getenv('GITHUB_TOKEN','')}
#   )

set -euo pipefail

DATE="${1:-$(date +%Y-%m-%d)}"
GITHUB_OWNER="${GITHUB_OWNER:-}"
GITHUB_REPO="${GITHUB_REPO:-ai-news-daily}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "ERROR: GITHUB_TOKEN not set. Cannot trigger deployment."
    echo "Please set GITHUB_TOKEN environment variable."
    exit 1
fi

if [ -z "$GITHUB_OWNER" ]; then
    echo "ERROR: GITHUB_OWNER not set."
    exit 1
fi

PAYLOAD=$(cat <<EOF
{
  "event_type": "deploy-news",
  "client_payload": {
    "date": "$DATE",
    "triggered_by": "pipeline"
  }
}
EOF
)

echo "Triggering GitHub Pages deployment for date=$DATE..."
echo "Repo: $GITHUB_OWNER/$GITHUB_REPO"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO/dispatches" \
    -d "$PAYLOAD")

if [ "$HTTP_CODE" = "204" ]; then
    echo "SUCCESS: Deployment triggered (HTTP 204)"
    echo "Check progress at: https://github.com/$GITHUB_OWNER/$GITHUB_REPO/actions"
else
    echo "ERROR: Failed to trigger deployment (HTTP $HTTP_CODE)"
    echo "Response:"
    curl -s -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO/dispatches" \
        -d "$PAYLOAD"
    exit 1
fi
