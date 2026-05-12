#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
# MSC Cargo — Predictive Maintenance: One-click deployment
#
# Usage:
#   ./deploy.sh                                    # deploy to dev (default)
#   ./deploy.sh -t prod                            # deploy to a specific target
#   ./deploy.sh --catalog my_cat --schema my_sch   # override variables
#   ./deploy.sh --host https://my-workspace.cloud.databricks.com
# ─────────────────────────────────────────────────────────────────────

TARGET="dev"
HOST=""
CATALOG=""
SCHEMA=""
WAREHOUSE_ID=""
SKIP_AUTH=false
SKIP_RUN=false

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Deploy the MSC Cargo Predictive Maintenance demo to a Databricks workspace.

Options:
  -t, --target TARGET         Bundle target (default: dev)
  -h, --host HOST             Workspace URL (overrides databricks.yml)
      --catalog CATALOG       Unity Catalog name
      --schema SCHEMA         Schema name
      --warehouse-id ID       SQL warehouse ID for the dashboard
      --skip-auth             Skip authentication step
      --skip-run              Deploy only, don't run the pipeline
      --help                  Show this help message

Examples:
  ./deploy.sh
  ./deploy.sh -t prod --host https://my-workspace.cloud.databricks.com
  ./deploy.sh --catalog my_catalog --schema my_schema
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--target)       TARGET="$2"; shift 2 ;;
    -h|--host)         HOST="$2"; shift 2 ;;
    --catalog)         CATALOG="$2"; shift 2 ;;
    --schema)          SCHEMA="$2"; shift 2 ;;
    --warehouse-id)    WAREHOUSE_ID="$2"; shift 2 ;;
    --skip-auth)       SKIP_AUTH=true; shift ;;
    --skip-run)        SKIP_RUN=true; shift ;;
    --help)            usage ;;
    *)                 echo "Unknown option: $1"; usage ;;
  esac
done

# ── Helpers ──────────────────────────────────────────────────────────

info()  { printf "\033[1;34m▶ %s\033[0m\n" "$1"; }
ok()    { printf "\033[1;32m✓ %s\033[0m\n" "$1"; }
fail()  { printf "\033[1;31m✗ %s\033[0m\n" "$1"; exit 1; }

# ── Pre-flight checks ───────────────────────────────────────────────

info "Pre-flight checks"

command -v databricks >/dev/null 2>&1 || fail "Databricks CLI not found. Install: brew install databricks/tap/databricks"
command -v git >/dev/null 2>&1        || fail "Git not found."

CLI_VERSION=$(databricks --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
ok "Databricks CLI v${CLI_VERSION}"

# ── Resolve variables for file upload paths ──────────────────────────

if [[ -n "$CATALOG" ]]; then
  RESOLVED_CATALOG="$CATALOG"
else
  RESOLVED_CATALOG=$(grep -A2 "^variables:" databricks.yml | grep -A1 "catalog:" | grep "default:" | awk '{print $2}' | head -1)
  [[ -z "$RESOLVED_CATALOG" ]] && RESOLVED_CATALOG="serverless_stable_3n0ihb_catalog"
fi

if [[ -n "$SCHEMA" ]]; then
  RESOLVED_SCHEMA="$SCHEMA"
else
  RESOLVED_SCHEMA=$(grep -A5 "^variables:" databricks.yml | grep -A1 "schema:" | grep "default:" | awk '{print $2}' | head -1)
  [[ -z "$RESOLVED_SCHEMA" ]] && RESOLVED_SCHEMA="msc_cargo_predictive_maintenance"
fi

VOLUME_PATH="/Volumes/${RESOLVED_CATALOG}/${RESOLVED_SCHEMA}/raw_data"

# Build --var flags
VAR_FLAGS=()
[[ -n "$CATALOG" ]]      && VAR_FLAGS+=(--var="catalog=${CATALOG}")
[[ -n "$SCHEMA" ]]       && VAR_FLAGS+=(--var="schema=${SCHEMA}")
[[ -n "$WAREHOUSE_ID" ]] && VAR_FLAGS+=(--var="warehouse_id=${WAREHOUSE_ID}")

# ── Step 1: Authenticate ────────────────────────────────────────────

if [[ "$SKIP_AUTH" == false ]]; then
  info "Step 1/6 — Authenticate"
  if [[ -n "$HOST" ]]; then
    databricks auth login --host "$HOST"
  else
    CONFIGURED_HOST=$(grep "host:" databricks.yml | head -1 | awk '{print $2}')
    if [[ -n "$CONFIGURED_HOST" ]]; then
      databricks auth login --host "$CONFIGURED_HOST" || true
    else
      echo "  No host found in databricks.yml. Pass --host or configure the target first."
      fail "Authentication failed"
    fi
  fi
  ok "Authenticated"
else
  info "Step 1/6 — Authenticate (skipped)"
fi

# ── Step 2: Validate ────────────────────────────────────────────────

info "Step 2/6 — Validate bundle"
databricks bundle validate -t "$TARGET" "${VAR_FLAGS[@]+"${VAR_FLAGS[@]}"}" || fail "Bundle validation failed"
ok "Bundle valid"

# ── Step 3: Deploy ──────────────────────────────────────────────────

info "Step 3/6 — Deploy resources (schema, volume, job, dashboard)"
databricks bundle deploy -t "$TARGET" "${VAR_FLAGS[@]+"${VAR_FLAGS[@]}"}" || fail "Deployment failed"
ok "Resources deployed"

# ── Step 4: Upload data ─────────────────────────────────────────────

info "Step 4/6 — Upload source data to volume"

for csv in files/equipment_master.csv files/work_orders.csv; do
  if [[ -f "$csv" ]]; then
    databricks fs cp "$csv" "${VOLUME_PATH}/$(basename "$csv")" --overwrite || fail "Failed to upload $csv"
    ok "Uploaded $(basename "$csv")"
  else
    fail "File not found: $csv"
  fi
done

# ── Step 5: Run pipeline ────────────────────────────────────────────

if [[ "$SKIP_RUN" == false ]]; then
  info "Step 5/6 — Run pipeline (setup_tables → predictive_maintenance)"
  databricks bundle run predictive_maintenance_pipeline -t "$TARGET" "${VAR_FLAGS[@]+"${VAR_FLAGS[@]}"}" || fail "Pipeline run failed"
  ok "Pipeline completed"
else
  info "Step 5/6 — Run pipeline (skipped)"
fi

# ── Step 6: Summary ─────────────────────────────────────────────────

info "Step 6/6 — Deployment complete!"

cat <<EOF

  ┌─────────────────────────────────────────────────────────┐
  │  MSC Cargo — Predictive Maintenance                     │
  │                                                         │
  │  Target:     ${TARGET}
  │  Catalog:    ${RESOLVED_CATALOG}
  │  Schema:     ${RESOLVED_SCHEMA}
  │  Volume:     ${VOLUME_PATH}
  │                                                         │
  │  Next steps:                                            │
  │  • Open the workspace and navigate to SQL → Dashboards  │
  │  • Look for "[${TARGET}] MSC Cargo — Predictive         │
  │    Maintenance"                                         │
  │                                                         │
  │  To tear down:                                          │
  │    databricks bundle destroy -t ${TARGET}
  └─────────────────────────────────────────────────────────┘
EOF
