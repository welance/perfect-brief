#!/bin/sh
# Welance node-chart env model: non-secret env is mounted at /app/.env.config
# (ConfigMap rendered from the tenant's envFileContent), secrets at
# /tmp/env_secret (1Password-backed onepassword-secret). Source both before
# starting; secrets win (sourced last). On bare docker-compose neither file
# exists, so this is a no-op and the compose-provided env is used as-is.
set -e

set -a
[ -f /app/.env.config ] && . /app/.env.config
[ -f /tmp/env_config ] && . /tmp/env_config
[ -f /tmp/env_secret ] && . /tmp/env_secret
set +a

exec "$@"
