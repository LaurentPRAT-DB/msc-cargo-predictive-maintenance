# MSC Cargo Predictive Maintenance

## Overview
Predictive maintenance demo for MSC Cargo. Clusters equipment defect descriptions using K-means on text embeddings to build a defect taxonomy, then evaluates data quality for ML-based maintenance scheduling.

## Databricks Target
- **Workspace**: https://fevm-serverless-stable-3n0ihb.cloud.databricks.com/
- **Catalog**: `serverless_stable_3n0ihb_catalog`
- **Schema**: `msc_cargo_predictive_maintenance`
- **Volume**: `raw_data` (CSV source files)
- **Workspace path**: `/Workspace/Users/laurent.prat@databricks.com/msc_cargo_predictive_maintenance/`

## Tables
- `equipment_master` — 50 equipment records (type, location, age, manufacturer, criticality)
- `work_orders` — 800 visit records with free-text defect descriptions across 7 failure modes
- `defect_features` — enriched output: records annotated with cluster, defect_cluster_name, quality scores
- `equipment_cluster_agg` — aggregated features per equipment unit

## Notebooks
- `00_setup_tables` — Loads CSVs from volume into Delta tables
- `01_predictive_maintenance` — Clustering pipeline: Delta → embeddings → K-means → defect taxonomy → feature table
