#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${1:?Service name required}"
REGION="${2:?Region required}"
WEB_SA="${3:?Portfolio web service account email required}"

AGENT_URL="$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --format='value(status.url)')"

if [[ -z "${AGENT_URL}" ]]; then
  echo "Could not resolve agent URL for ${SERVICE_NAME}" >&2
  exit 1
fi

TOKEN="$(gcloud auth print-identity-token \
  --impersonate-service-account="${WEB_SA}" \
  --audiences="${AGENT_URL}")"

RESPONSE="$(curl -sf -H "Authorization: Bearer ${TOKEN}" "${AGENT_URL}/health")"
echo "${RESPONSE}"

python3 -c "
import json, sys
data = json.loads(sys.argv[1])
assert data.get('status') == 'ok', data
assert data.get('llm_configured') is True, data
print('Agent health check passed')
" "${RESPONSE}"
