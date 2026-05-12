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
#
# Configuration is read from config.yml (edit for your workspace).
# CLI flags override config.yml values.
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

Configuration is read from config.yml. CLI flags override config values.

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

# ── Load config.yml ──────────────────────────────────────────────────

CONFIG_FILE="config.yml"
CONFIG_CATALOG=""
CONFIG_SCHEMA=""
CONFIG_WAREHOUSE=""

if [[ -f "$CONFIG_FILE" ]]; then
  CONFIG_CATALOG=$(grep '^catalog:' "$CONFIG_FILE" | awk '{print $2}' | head -1)
  CONFIG_SCHEMA=$(grep '^schema:' "$CONFIG_FILE" | awk '{print $2}' | head -1)
  CONFIG_WAREHOUSE=$(grep '^warehouse_id:' "$CONFIG_FILE" | awk '{print $2}' | head -1)
fi

# Resolve: CLI flag > config.yml > hardcoded fallback
RESOLVED_CATALOG="${CATALOG:-${CONFIG_CATALOG:-serverless_stable_3n0ihb_catalog}}"
RESOLVED_SCHEMA="${SCHEMA:-${CONFIG_SCHEMA:-msc_cargo_predictive_maintenance}}"
RESOLVED_WAREHOUSE="${WAREHOUSE_ID:-${CONFIG_WAREHOUSE:-b868e84cedeb4262}}"

VOLUME_PATH="/Volumes/${RESOLVED_CATALOG}/${RESOLVED_SCHEMA}/raw_data"

# Build --var flags for bundle commands
VAR_FLAGS=(--var="catalog=${RESOLVED_CATALOG}" --var="schema=${RESOLVED_SCHEMA}" --var="warehouse_id=${RESOLVED_WAREHOUSE}")

# ── Pre-flight checks ───────────────────────────────────────────────

info "Pre-flight checks"

command -v databricks >/dev/null 2>&1 || fail "Databricks CLI not found. Install: brew install databricks/tap/databricks"
command -v git >/dev/null 2>&1        || fail "Git not found."

CLI_VERSION=$(databricks --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
ok "Databricks CLI v${CLI_VERSION}"
ok "Config: catalog=${RESOLVED_CATALOG}, schema=${RESOLVED_SCHEMA}"

# ── Step 1: Authenticate ────────────────────────────────────────────

if [[ "$SKIP_AUTH" == false ]]; then
  info "Step 1/7 — Authenticate"
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
  info "Step 1/7 — Authenticate (skipped)"
fi

# ── Step 2: Check/Create Catalog ────────────────────────────────────

info "Step 2/7 — Check catalog '${RESOLVED_CATALOG}' exists"

if databricks catalogs get "$RESOLVED_CATALOG" &>/dev/null; then
  ok "Catalog '${RESOLVED_CATALOG}' exists"
else
  info "Catalog '${RESOLVED_CATALOG}' not found — creating..."
  if databricks catalogs create "$RESOLVED_CATALOG" &>/dev/null; then
    ok "Catalog '${RESOLVED_CATALOG}' created"
  else
    fail "Failed to create catalog '${RESOLVED_CATALOG}'. Check permissions or create it manually."
  fi
fi

# ── Step 3: Validate ────────────────────────────────────────────────

info "Step 3/7 — Validate bundle"
databricks bundle validate -t "$TARGET" "${VAR_FLAGS[@]}" || fail "Bundle validation failed"
ok "Bundle valid"

# ── Step 4: Deploy ──────────────────────────────────────────────────

info "Step 4/7 — Deploy resources (schema, volume, job, dashboard)"
databricks bundle deploy -t "$TARGET" "${VAR_FLAGS[@]}" || fail "Deployment failed"
ok "Resources deployed"

# ── Step 5: Upload data ─────────────────────────────────────────────

info "Step 5/7 — Upload source data to volume"

for csv in files/equipment_master.csv files/work_orders.csv; do
  if [[ -f "$csv" ]]; then
    databricks fs cp "$csv" "${VOLUME_PATH}/$(basename "$csv")" --overwrite || fail "Failed to upload $csv"
    ok "Uploaded $(basename "$csv")"
  else
    fail "File not found: $csv"
  fi
done

# ── Step 6: Run pipeline ────────────────────────────────────────────

if [[ "$SKIP_RUN" == false ]]; then
  info "Step 6/7 — Run pipeline (setup_tables → predictive_maintenance)"
  databricks bundle run predictive_maintenance_pipeline -t "$TARGET" "${VAR_FLAGS[@]}" || fail "Pipeline run failed"
  ok "Pipeline completed"
else
  info "Step 6/7 — Run pipeline (skipped)"
fi

# ── Step 7: Summary ─────────────────────────────────────────────────

info "Step 7/7 — Deployment complete!"

cat <<EOF

  ┌─────────────────────────────────────────────────────────┐
  │  MSC Cargo — Predictive Maintenance                     │
  │                                                         │
  │  Target:     ${TARGET}
  │  Catalog:    ${RESOLVED_CATALOG}
  │  Schema:     ${RESOLVED_SCHEMA}
  │  Warehouse:  ${RESOLVED_WAREHOUSE}
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
