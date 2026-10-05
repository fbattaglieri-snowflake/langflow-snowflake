#!/bin/sh
set -eu

# Block mounts start root-owned. Never mount storage over application code.
DATA_DIR=/persist
if [ "$(id -u)" = 0 ]; then
    mkdir -p "$DATA_DIR/config" "$DATA_DIR/storage" "$DATA_DIR/knowledge_bases"
    chown -R 1000:0 "$DATA_DIR"
    chmod 0770 "$DATA_DIR"
    exec setpriv --reuid=1000 --regid=0 --init-groups -- "$0" "$@"
fi
if [ ! -w "$DATA_DIR" ]; then
    echo "Persistent storage is not writable; refusing ephemeral startup" >&2
    exit 1
fi
: "${LANGFLOW_SECRET_KEY:?Supply the persistent encryption secret}"
: "${LANGFLOW_SUPERUSER:?Supply the application administrator name}"
: "${LANGFLOW_SUPERUSER_PASSWORD:?Supply the application administrator password}"
export LANGFLOW_CONFIG_DIR="$DATA_DIR/config"
export LANGFLOW_DATABASE_URL="sqlite:///$DATA_DIR/langflow.db"
export LANGFLOW_KNOWLEDGE_BASES_DIR="$DATA_DIR/knowledge_bases"
export LANGFLOW_AUTO_LOGIN=false
export LANGFLOW_NEW_USER_IS_ACTIVE=false
export LANGFLOW_HOST=0.0.0.0
export LANGFLOW_PORT=7860
export LANGFLOW_OPEN_BROWSER=false
export DO_NOT_TRACK=true
exec langflow run "$@"