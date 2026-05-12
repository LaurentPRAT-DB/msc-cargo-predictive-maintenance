# MSC Cargo — Predictive Maintenance Framework

## Objective

This project implements a **predictive maintenance solution** for MSC Cargo equipment by analysing free-text defect descriptions recorded during field inspections.

The pipeline:
1. Ingests unstructured maintenance records from a Delta table
2. Filters records by a composite **data quality score** (frequency, freshness, completeness, pertinence)
3. Generates text embeddings from defect descriptions (TF-IDF locally, Databricks BGE-M3 in production)
4. Runs **K-means clustering** with silhouette-based tuning to discover a defect taxonomy automatically
5. Validates clusters against ground-truth labels using the Adjusted Rand Index (ARI)
6. Writes an enriched **feature table** back to Delta — ready to feed downstream ML models for maintenance window prediction and parts classification

---

## Datasets

All source data resides in the Unity Catalog volume:  
`/Volumes/serverless_stable_3n0ihb_catalog/msc_cargo_predictive_maintenance/raw_data/`

### work_orders.csv — 800 records

Each row represents a single maintenance visit to one of 50 equipment units.

| Column | Description |
|--------|-------------|
| `record_id` | Unique work order identifier (WO-00001 … WO-00800) |
| `equipment_id` | Equipment unit (EQ-0001 … EQ-0050) |
| `equipment_type` | Centrifugal Pump, Air Compressor, Heat Exchanger, Electric Motor, Hydraulic Press, Conveyor Belt, Cooling Tower, Gearbox |
| `location` | Plant / line location |
| `visit_date` | Date of inspection (2022-01-01 to 2023-12-31) |
| `technician_id` | Technician who performed the visit |
| `defect_description` | Free-text narrative describing the observed defect — the primary input for clustering |
| `true_defect_label` | Ground-truth failure mode (7 classes: bearing_wear, seal_leak, overheating, vibration, electrical_fault, corrosion, lubrication) |
| `severity` | High / Medium / Low |
| `days_to_failure` | Days until actual failure occurred (null if still operating) |
| `repair_duration_hrs` | Time spent on repair |
| `downtime_hrs` | Equipment downtime caused |
| `parts_replaced` | Replacement part used |
| `data_quality_frequency` | Quality dimension: how often this equipment is monitored (0–1) |
| `data_quality_freshness` | Quality dimension: recency of the data (0–1) |
| `data_quality_completeness` | Quality dimension: completeness of the record (0–1) |
| `data_quality_pertinence` | Quality dimension: relevance to maintenance decisions (0–1) |
| `quality_score` | Weighted composite score (0–1) |

### equipment_master.csv — 50 records

One row per equipment unit with static attributes.

| Column | Description |
|--------|-------------|
| `equipment_id` | Primary key |
| `equipment_type` | Category of equipment |
| `location` | Physical location |
| `installation_year` | Year installed (2010–2022) |
| `age_years` | Calculated age |
| `manufacturer` | Siemens, ABB, Grundfos, Atlas Copco, SKF |
| `criticality` | High / Medium / Low |

### defect_features.csv — 792 records (output)

The enriched feature table produced by the clustering notebook. Each record from `work_orders` that passed the quality filter is annotated with its cluster assignment and cluster name.

### equipment_cluster_agg.csv — 50 records (output)

One row per equipment unit with aggregated features derived from the clustering results:

| Column | Description |
|--------|-------------|
| `total_visits` | Number of maintenance visits |
| `distinct_defects` | Number of distinct defect clusters observed |
| `avg_quality_score` | Mean data quality across visits |
| `avg_repair_hrs` | Average repair time |
| `avg_downtime_hrs` | Average downtime per visit |
| `pct_high_severity` | Proportion of high-severity events |
| `last_visit_date` | Most recent visit |

---

## How to Run

### Prerequisites

- Access to workspace: `https://fevm-serverless-stable-3n0ihb.cloud.databricks.com/`
- Notebooks are located at:  
  `/Workspace/Users/laurent.prat@databricks.com/msc_cargo_predictive_maintenance/notebooks/`

### Step 1 — Create Delta tables (run once)

Open and run **`00_setup_tables`**

This notebook reads the 4 CSV files from the volume and creates the Delta tables `equipment_master` and `work_orders` in the schema `serverless_stable_3n0ihb_catalog.msc_cargo_predictive_maintenance`.

- **Compute**: Serverless or any cluster with Unity Catalog access
- **Runtime**: ~30 seconds
- **Outcome**: Two Delta tables ready for the clustering pipeline

### Step 2 — Run the clustering pipeline

Open and run **`01_predictive_maintenance`**

This notebook executes the full defect clustering pipeline:

| Cell | Stage | What it does |
|------|-------|-------------|
| 0 | Dependencies | Installs `umap-learn`, restarts Python |
| 1 | Load | Reads Delta tables into Pandas DataFrames |
| 2 | Quality filter | Excludes records below 0.50 quality score |
| 3 | Embeddings | TF-IDF (3000 features, 1-2 grams) → SVD (64 dims) → L2 normalisation |
| 4 | K-means tuning | Sweeps k=4…13, selects best silhouette score |
| 5 | Final model | Fits K-means with best k |
| 6 | Merge small clusters | Clusters below 20 members → "Other" bucket |
| 7 | Labelling | Extracts top TF-IDF terms per cluster for naming |
| 8 | Validation | Computes ARI vs ground truth, generates confusion heatmap |
| 9 | UMAP | 2D projection for visual cluster inspection |
| 10 | Write | Saves `defect_features` and `equipment_cluster_agg` as Delta tables |
| 11 | Summary | Prints final statistics |

- **Compute**: Serverless recommended (no cluster required)
- **Runtime**: ~60 seconds
- **Outcome**: Two output Delta tables + visualisations (saved as PNG in the volume)

### Expected Results

- **Best k**: 13 clusters (silhouette-optimised)
- **Named clusters**: Bearing Wear, Vibration, Seal Leak, Overheating, Lubrication, Electrical Fault, Corrosion
- **ARI**: ~0.17 (expected with TF-IDF; improves significantly with BGE-M3 embeddings)
- **Plots saved** to volume: quality distribution, silhouette/elbow curves, confusion heatmap, cluster sizes, UMAP projection

---

## Production Upgrade Path

To improve clustering accuracy in production, replace the TF-IDF embedding step (Cell 3) with the Databricks Foundation Model endpoint:

```python
from mlflow.deployments import get_deploy_client
client = get_deploy_client("databricks")

def embed_batch(texts, batch_size=64):
    vecs = []
    for i in range(0, len(texts), batch_size):
        resp = client.predict(
            endpoint="databricks-bge-large-en",
            inputs={"input": texts[i:i+batch_size]}
        )
        vecs.extend([r["embedding"] for r in resp["data"]])
    return np.array(vecs)

embeddings = embed_batch(df_clean["defect_description"].tolist())
```

This yields higher ARI (0.5+) because contextual embeddings better separate overlapping vocabulary (e.g. "temperature" in overheating vs. bearing wear contexts).

---

## Schema Reference

```
serverless_stable_3n0ihb_catalog.msc_cargo_predictive_maintenance
├── equipment_master        (Delta table — input)
├── work_orders             (Delta table — input)
├── defect_features         (Delta table — output)
├── equipment_cluster_agg   (Delta table — output)
└── raw_data/               (Volume — source CSVs + plots)
    ├── equipment_master.csv
    ├── work_orders.csv
    ├── defect_features.csv
    ├── equipment_cluster_agg.csv
    └── *.png (generated plots)
```
