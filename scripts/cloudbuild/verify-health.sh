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

for attempt in $(seq 1 30); do
  if RESPONSE="$(curl -sf -H "Authorization: Bearer ${TOKEN}" "${AGENT_URL}/health")"; then
    if python3 -c "
import json, sys
data = json.loads(sys.argv[1])
sys.exit(0 if data.get('status') == 'ok' and data.get('llm_configured') is True else 1)
" "${RESPONSE}"; then
      echo "${RESPONSE}"
      echo "Agent health check passed"
      exit 0
    fi
    echo "Attempt ${attempt}: agent not ready yet — ${RESPONSE}"
  else
    echo "Attempt ${attempt}: health request failed"
  fi
  sleep 10
done

echo "Agent did not become healthy in time" >&2
exit 1
