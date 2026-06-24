#!/usr/bin/env bash
set -euo pipefail

SECRET_NAME="${1:?Secret name required}"

gcloud secrets versions access latest --secret="${SECRET_NAME}" >/dev/null
echo "Secret ${SECRET_NAME} is available"
