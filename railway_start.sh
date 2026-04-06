#!/bin/bash
# True 24/7 Autonomy Cloud Boot Script for VisionEdge Agent
echo "[System] Railway container starting..."

# Dump Railway Environment Variables into a fresh secrets.json file
# so the agent Python scripts can read them natively without code changes.
echo "[System] Generating generic secrets.json from Railway Variables..."
cat << EOF > secrets.json
{
    "DATABASE_URL": "${DATABASE_URL:-}",
    "CREATOMATE_API_KEY": "${CREATOMATE_API_KEY:-}",
    "CREATOMATE_TEMPLATE_ID": "${CREATOMATE_TEMPLATE_ID:-}",
    "R2_ACCOUNT_ID": "${R2_ACCOUNT_ID:-}",
    "R2_ACCESS_KEY_ID": "${R2_ACCESS_KEY_ID:-}",
    "R2_SECRET_ACCESS_KEY": "${R2_SECRET_ACCESS_KEY:-}",
    "R2_BUCKET_NAME": "${R2_BUCKET_NAME:-}",
    "R2_PUBLIC_URL": "${R2_PUBLIC_URL:-}",
    "UPLOAD_POST_API_KEY": "${UPLOAD_POST_API_KEY:-}",
    "OPENAI_API_KEY": "${OPENAI_API_KEY:-}",
    "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY:-}",
    "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY:-}",
    "FAL_KEY": "${FAL_KEY:-}",
    "TWITTER_API_KEY": "${TWITTER_API_KEY:-}",
    "TWITTER_API_SECRET": "${TWITTER_API_SECRET:-}",
    "TWITTER_ACCESS_TOKEN": "${TWITTER_ACCESS_TOKEN:-}",
    "TWITTER_ACCESS_SECRET": "${TWITTER_ACCESS_SECRET:-}"
}
EOF

echo "[System] Secrets bridge established."
echo "[System] Launching the Autonomous Agent Scheduler..."

# Execute the agent and keep the process alive
# We export PYTHONPATH so local imports in the tools dir resolve properly
export PYTHONPATH=.tmp/pkgs
python tools/marketing/agent_scheduler.py
