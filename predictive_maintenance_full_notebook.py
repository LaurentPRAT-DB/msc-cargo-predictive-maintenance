import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import random

random.seed(42)
np.random.seed(42)

# ── Equipment master ──────────────────────────────────────────────────────────
equipment_types = ["Centrifugal Pump", "Air Compressor", "Heat Exchanger",
                   "Electric Motor", "Hydraulic Press", "Conveyor Belt",
                   "Cooling Tower", "Gearbox"]

locations = ["Plant A - Line 1", "Plant A - Line 2", "Plant B - Line 1",
             "Plant B - Line 3", "Warehouse C", "Utilities Block"]

equipment_rows = []
for i in range(1, 51):
    install_year = random.randint(2010, 2022)
    equipment_rows.append({
        "equipment_id": f"EQ-{i:04d}",
        "equipment_type": random.choice(equipment_types),
        "location": random.choice(locations),
        "installation_year": install_year,
        "age_years": 2024 - install_year,
        "manufacturer": random.choice(["Siemens", "ABB", "Grundfos", "Atlas Copco", "SKF"]),
        "criticality": random.choice(["High", "High", "Medium", "Medium", "Low"]),
    })

df_equipment = pd.DataFrame(equipment_rows)

# ── Defect templates per failure mode ─────────────────────────────────────────
defect_templates = {
    "bearing_wear": [
        "Unusual noise detected in bearing housing, suspected wear on inner race",
        "Bearing temperature elevated to {temp}°C during operation, vibration increasing",
        "High-pitched squealing noise from bearing assembly, lubrication appears insufficient",
        "Bearing play exceeding tolerance, axial movement of {mm}mm observed",
        "Metal particles found in oil sample, bearing degradation confirmed",
        "Bearing vibration amplitude {vib} mm/s RMS, trending upward over last {days} days",
        "Grease discolouration and hardening noted around bearing cap",
    ],
    "seal_leak": [
        "Mechanical seal leaking at shaft interface, fluid loss approx {rate} ml/hr",
        "Oil seepage observed around pump casing seal, minor pooling on floor",
        "Dynamic seal failure suspected, pressure drop of {pct}% noted in system",
        "Seal face wear visible during inspection, scoring on stationary ring",
        "Lip seal deteriorated, grease escaping from gearbox output shaft",
        "Hydraulic fluid leak at cylinder rod seal, {rate} ml/hr estimated loss",
        "O-ring compression set failure, intermittent leak under high pressure",
    ],
    "overheating": [
        "Motor winding temperature reached {temp}°C, thermal protection triggered",
        "Cooling fan obstructed by debris, motor surface temperature {temp}°C",
        "Heat exchanger fouling reducing efficiency, outlet temp {temp}°C above setpoint",
        "Overheating on drive-end bearing, infrared scan shows hot spot at {temp}°C",
        "Compressor discharge temperature {temp}°C, intercooler bypass suspected",
        "Electrical cabinet temperature {temp}°C due to failed ventilation fan",
        "Gearbox oil temperature {temp}°C, possible cooler blockage",
    ],
    "vibration": [
        "Excessive vibration on pump casing, amplitude {vib} mm/s at {rpm} RPM",
        "Unbalance detected on rotating assembly, vibration {vib} mm/s 1X component",
        "Misalignment between motor and gearbox shaft, {vib} mm/s 2X vibration",
        "Structural resonance observed at {rpm} RPM, bolts found loose on baseplate",
        "Cavitation noise and vibration in pump, inlet pressure below NPSH",
        "Belt tension incorrect causing vibration and premature wear",
        "Impeller damage suspected, broadband vibration increase {vib} mm/s",
    ],
    "electrical_fault": [
        "Insulation resistance measured at {mohm} MΩ, below {threshold} MΩ minimum",
        "Phase imbalance detected, current draw {pct}% higher on L2",
        "Contactor pitting observed, intermittent contact causing voltage dips",
        "Motor winding resistance out of tolerance, possible turn-to-turn short",
        "VFD fault code F{code} logged, overcurrent on deceleration",
        "Earth leakage current {ma}mA detected, isolation check required",
        "Capacitor bank showing reduced capacitance, power factor {pf} below target",
    ],
    "corrosion": [
        "Surface corrosion on pipe flanges, pitting depth approx {mm}mm",
        "Internal corrosion found on heat exchanger tubes during inspection",
        "Rust deposits blocking strainer, pressure differential {psi} PSI across filter",
        "Galvanic corrosion at dissimilar metal joint, wall thickness reduced",
        "Chemical attack on pump impeller, material loss estimated {pct}%",
        "Corrosion under insulation (CUI) suspected on horizontal pipe section",
        "Coating failure on tank exterior, rust streaks visible below insulation",
    ],
    "lubrication": [
        "Oil level low in gearbox sight glass, top-up of {litres}L required",
        "Lubricant contamination detected, water content {pct}% above limit",
        "Oil analysis shows high iron content {ppm} ppm, internal wear indicated",
        "Grease nipple blocked, bearing running dry for estimated {days} days",
        "Wrong lubricant grade used during last service, compatibility issue",
        "Oil viscosity out of specification, degraded due to thermal cycling",
        "Automatic lubrication system failed, manual greasing required",
    ],
}

def fill_template(template):
    return template.format(
        temp=random.randint(65, 120),
        mm=round(random.uniform(0.1, 2.5), 2),
        vib=round(random.uniform(2.0, 18.0), 1),
        days=random.randint(3, 45),
        rate=random.randint(5, 200),
        pct=random.randint(5, 40),
        rpm=random.choice([750, 1000, 1450, 1500, 3000]),
        mohm=random.randint(1, 50),
        threshold=100,
        ma=round(random.uniform(5, 80), 1),
        pf=round(random.uniform(0.6, 0.85), 2),
        code=random.randint(1, 99),
        psi=random.randint(5, 30),
        ppm=random.randint(50, 400),
        litres=round(random.uniform(0.5, 5.0), 1),
    )

# ── Visit / work order records ─────────────────────────────────────────────────
defect_keys = list(defect_templates.keys())
severity_map = {"bearing_wear": "Medium", "seal_leak": "Medium", "overheating": "High",
                "vibration": "Medium", "electrical_fault": "High",
                "corrosion": "Low", "lubrication": "Low"}

records = []
base_date = datetime(2022, 1, 1)

for i in range(1, 801):
    equip = random.choice(equipment_rows)
    true_defect = random.choices(
        defect_keys,
        weights=[20, 15, 12, 18, 10, 10, 15],  # bearing & vibration most common
        k=1
    )[0]
    templates = defect_templates[true_defect]
    description = fill_template(random.choice(templates))

    # Add some noise / multi-issue descriptions
    if random.random() < 0.2:
        extra_defect = random.choice(defect_keys)
        description += ". Additionally, " + fill_template(random.choice(defect_templates[extra_defect])).lower()

    visit_date = base_date + timedelta(days=random.randint(0, 730))
    days_to_failure = random.randint(1, 180) if random.random() < 0.6 else None
    repair_duration_hrs = round(random.uniform(0.5, 16.0), 1)
    downtime_hrs = round(random.uniform(0, repair_duration_hrs * 1.5), 1)

    records.append({
        "record_id": f"WO-{i:05d}",
        "equipment_id": equip["equipment_id"],
        "equipment_type": equip["equipment_type"],
        "location": equip["location"],
        "visit_date": visit_date.strftime("%Y-%m-%d"),
        "technician_id": f"TECH-{random.randint(1, 20):03d}",
        "defect_description": description,
        "true_defect_label": true_defect,       # ground truth (hidden from model)
        "severity": severity_map[true_defect],
        "days_to_failure": days_to_failure,
        "repair_duration_hrs": repair_duration_hrs,
        "downtime_hrs": downtime_hrs,
        "parts_replaced": random.choice([
            "Bearing 6205-2RS", "Mechanical seal kit", "O-ring set",
            "Contactor 3RT2", "Oil filter + 5L oil", "Coupling insert",
            "None - monitoring", "Impeller", "Capacitor 40µF",
        ]),
        "data_quality_frequency": round(random.uniform(0.3, 1.0), 2),
        "data_quality_freshness": round(random.uniform(0.4, 1.0), 2),
        "data_quality_completeness": round(random.uniform(0.5, 1.0), 2),
        "data_quality_pertinence": round(random.uniform(0.4, 1.0), 2),
    })

df_records = pd.DataFrame(records)
df_records["quality_score"] = (
    df_records["data_quality_frequency"] * 0.25 +
    df_records["data_quality_freshness"] * 0.30 +
    df_records["data_quality_completeness"] * 0.25 +
    df_records["data_quality_pertinence"] * 0.20
).round(3)

# ── Save ──────────────────────────────────────────────────────────────────────
df_equipment.to_csv("/home/claude/predictive_maintenance/equipment_master.csv", index=False)
df_records.to_csv("/home/claude/predictive_maintenance/work_orders.csv", index=False)

print(f"Equipment rows : {len(df_equipment)}")
print(f"Work order rows: {len(df_records)}")
print(f"\nDefect distribution:")
print(df_records["true_defect_label"].value_counts().to_string())
print(f"\nSample record:\n{df_records.iloc[0]['defect_description']}")
# Databricks notebook source
# MAGIC %md
# MAGIC # Predictive Maintenance — Defect Clustering Notebook
# MAGIC **Pipeline:** Delta table → Text embeddings → K-means tuning → Defect taxonomy → Feature table
# MAGIC
# MAGIC > On Databricks replace the TF-IDF embedder with the Mosaic AI embedding endpoint.
# MAGIC > Everything else (K-means, silhouette tuning, feature writing) is identical.

# COMMAND ----------
# MAGIC %md ## 0 · Imports & config

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import warnings, os
warnings.filterwarnings("ignore")

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans
from sklearn.metrics import (silhouette_score, adjusted_rand_score,
                             confusion_matrix, classification_report)
from sklearn.preprocessing import normalize

OUTPUT_DIR = "/home/claude/predictive_maintenance/plots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

RANDOM_STATE   = 42
MIN_CLUSTER_SIZE = 20      # clusters smaller than this → merged into "Other"
K_RANGE        = range(4, 14)   # search space for k
EMBED_DIM      = 64        # SVD components (≈ BERT 768 in spirit)

np.random.seed(RANDOM_STATE)

print("Config ready.")

# COMMAND ----------
# MAGIC %md ## 1 · Load Delta table (simulated as CSV)
# MAGIC
# MAGIC On Databricks this would be:
# MAGIC ```python
# MAGIC df = spark.read.format("delta").load("/mnt/maintenance/work_orders").toPandas()
# MAGIC ```

df_raw = pd.read_csv("/home/claude/predictive_maintenance/work_orders.csv")
df_eq  = pd.read_csv("/home/claude/predictive_maintenance/equipment_master.csv")

print(f"Work orders : {len(df_raw):,}")
print(f"Equipment   : {len(df_eq):,}")
print(f"Date range  : {df_raw['visit_date'].min()} → {df_raw['visit_date'].max()}")
print(f"\nColumns:\n{list(df_raw.columns)}")

# COMMAND ----------
# MAGIC %md ## 2 · Data quality filter
# MAGIC
# MAGIC Records with a composite quality score below 0.5 are excluded from clustering.
# MAGIC They still feed the ML model but with a down-weighted sample weight.

df = df_raw.copy()
df["quality_score"] = (
    df["data_quality_frequency"]    * 0.25 +
    df["data_quality_freshness"]    * 0.30 +
    df["data_quality_completeness"] * 0.25 +
    df["data_quality_pertinence"]   * 0.20
).round(3)

QUALITY_THRESHOLD = 0.50
df_clean  = df[df["quality_score"] >= QUALITY_THRESHOLD].copy().reset_index(drop=True)
df_low_q  = df[df["quality_score"] <  QUALITY_THRESHOLD].copy()

print(f"Records passing quality filter : {len(df_clean):,}  ({len(df_clean)/len(df)*100:.1f}%)")
print(f"Records excluded (low quality) : {len(df_low_q):,}")
print(f"\nQuality score stats:\n{df_clean['quality_score'].describe().round(3).to_string()}")

# ── Quality distribution plot ────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 3.5))
ax.hist(df["quality_score"], bins=30, color="#534AB7", alpha=0.75, edgecolor="white", linewidth=0.5)
ax.axvline(QUALITY_THRESHOLD, color="#D85A30", lw=1.5, linestyle="--", label=f"Threshold {QUALITY_THRESHOLD}")
ax.set_xlabel("Quality score", fontsize=11)
ax.set_ylabel("Record count", fontsize=11)
ax.set_title("Data quality score distribution", fontsize=12, fontweight="500")
ax.legend(fontsize=10)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/01_quality_distribution.png", dpi=140)
plt.close()
print("Saved → 01_quality_distribution.png")

# COMMAND ----------
# MAGIC %md ## 3 · Text embedding
# MAGIC
# MAGIC **Local / CI:** TF-IDF (1-2 grams) → TruncatedSVD (64 dims) → L2 normalise.
# MAGIC
# MAGIC **Databricks production swap-in:**
# MAGIC ```python
# MAGIC from mlflow.deployments import get_deploy_client
# MAGIC client = get_deploy_client("databricks")
# MAGIC
# MAGIC def embed_batch(texts, batch_size=64):
# MAGIC     vecs = []
# MAGIC     for i in range(0, len(texts), batch_size):
# MAGIC         batch = texts[i:i+batch_size]
# MAGIC         resp  = client.predict(
# MAGIC             endpoint="databricks-bge-large-en",
# MAGIC             inputs={"input": batch}
# MAGIC         )
# MAGIC         vecs.extend([r["embedding"] for r in resp["data"]])
# MAGIC     return np.array(vecs)
# MAGIC
# MAGIC embeddings = embed_batch(df_clean["defect_description"].tolist())
# MAGIC ```

print("Fitting TF-IDF vectoriser …")
tfidf = TfidfVectorizer(
    max_features=3000,
    ngram_range=(1, 2),
    stop_words="english",
    sublinear_tf=True,
    min_df=2,
)
X_tfidf = tfidf.fit_transform(df_clean["defect_description"])
print(f"  Vocabulary size : {X_tfidf.shape[1]:,}")

print("Reducing dimensions with TruncatedSVD …")
svd = TruncatedSVD(n_components=EMBED_DIM, random_state=RANDOM_STATE)
X_svd = svd.fit_transform(X_tfidf)
print(f"  Explained variance retained : {svd.explained_variance_ratio_.sum():.1%}")

# L2 normalise (makes cosine distance equivalent to euclidean on unit sphere)
embeddings = normalize(X_svd, norm="l2")
print(f"  Final embedding shape : {embeddings.shape}")

# COMMAND ----------
# MAGIC %md ## 4 · K-means tuning — silhouette search
# MAGIC
# MAGIC We sweep k from 4 → 13 and pick the k that maximises the silhouette score.
# MAGIC The elbow of the inertia curve is shown as a secondary signal.

print(f"Sweeping k in {list(K_RANGE)} …")
results = []

for k in K_RANGE:
    km = KMeans(n_clusters=k, init="k-means++", n_init=10,
                max_iter=300, random_state=RANDOM_STATE)
    labels = km.fit_predict(embeddings)
    sil    = silhouette_score(embeddings, labels, sample_size=min(2000, len(embeddings)),
                              random_state=RANDOM_STATE)
    results.append({"k": k, "inertia": km.inertia_, "silhouette": sil})
    print(f"  k={k:2d}  inertia={km.inertia_:,.0f}  silhouette={sil:.4f}")

df_results = pd.DataFrame(results)
best_k = int(df_results.loc[df_results["silhouette"].idxmax(), "k"])
print(f"\n✔ Best k = {best_k}  (silhouette = {df_results.loc[df_results['k']==best_k,'silhouette'].values[0]:.4f})")

# ── Silhouette + inertia plot ─────────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

ax1.plot(df_results["k"], df_results["silhouette"], "o-", color="#534AB7", lw=2, ms=6)
ax1.axvline(best_k, color="#D85A30", lw=1.5, linestyle="--", label=f"Best k={best_k}")
ax1.set_xlabel("Number of clusters (k)", fontsize=11)
ax1.set_ylabel("Silhouette score", fontsize=11)
ax1.set_title("Silhouette score vs k", fontsize=12, fontweight="500")
ax1.legend(fontsize=10); ax1.spines[["top","right"]].set_visible(False)

ax2.plot(df_results["k"], df_results["inertia"], "s-", color="#0F6E56", lw=2, ms=6)
ax2.axvline(best_k, color="#D85A30", lw=1.5, linestyle="--", label=f"Best k={best_k}")
ax2.set_xlabel("Number of clusters (k)", fontsize=11)
ax2.set_ylabel("Inertia (WCSS)", fontsize=11)
ax2.set_title("Elbow curve", fontsize=12, fontweight="500")
ax2.legend(fontsize=10); ax2.spines[["top","right"]].set_visible(False)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/02_kmeans_tuning.png", dpi=140)
plt.close()
print("Saved → 02_kmeans_tuning.png")

# COMMAND ----------
# MAGIC %md ## 5 · Final model — fit with best k

km_final = KMeans(n_clusters=best_k, init="k-means++", n_init=20,
                  max_iter=500, random_state=RANDOM_STATE)
df_clean["cluster_raw"] = km_final.fit_predict(embeddings)

# Cluster size check
cluster_sizes = df_clean["cluster_raw"].value_counts().sort_index()
print("Cluster sizes (raw):")
print(cluster_sizes.to_string())

# COMMAND ----------
# MAGIC %md ## 6 · Minimum threshold — merge small clusters into "Other"
# MAGIC
# MAGIC Any cluster with fewer than `MIN_CLUSTER_SIZE` members is relabelled −1 ("Other").
# MAGIC This avoids over-splitting sparse noise into spurious defect types.

small_clusters = cluster_sizes[cluster_sizes < MIN_CLUSTER_SIZE].index.tolist()
print(f"Clusters below min threshold ({MIN_CLUSTER_SIZE}): {small_clusters}")

df_clean["cluster"] = df_clean["cluster_raw"].apply(
    lambda c: -1 if c in small_clusters else c
)

# Re-index surviving clusters 0..N
surviving = sorted([c for c in df_clean["cluster"].unique() if c != -1])
remap = {old: new for new, old in enumerate(surviving)}
remap[-1] = -1
df_clean["cluster"] = df_clean["cluster"].map(remap)

n_clusters_final = df_clean[df_clean["cluster"] >= 0]["cluster"].nunique()
print(f"\nFinal cluster count : {n_clusters_final}  (+1 'Other' bucket)")
print(df_clean["cluster"].value_counts().sort_index().to_string())

# COMMAND ----------
# MAGIC %md ## 7 · Automatic cluster labelling
# MAGIC
# MAGIC For each cluster we extract the top TF-IDF terms from member documents.
# MAGIC On Databricks you can replace this with an LLM call (Llama 3 / Claude via
# MAGIC Model Serving) passing the top-5 documents to generate a one-line label.

def label_cluster(cluster_id, df_c, tfidf_model, top_n=8):
    """Return the top n TF-IDF terms for documents in this cluster."""
    mask   = df_c["cluster"] == cluster_id
    subset = df_c.loc[mask, "defect_description"]
    X_sub  = tfidf_model.transform(subset)
    scores = np.asarray(X_sub.mean(axis=0)).flatten()
    top_i  = scores.argsort()[::-1][:top_n]
    terms  = [tfidf_model.get_feature_names_out()[i] for i in top_i]
    return terms

# Human-friendly names (in production: LLM generates these)
CLUSTER_NAMES = {
    -1: "Other / Unclassified",
     0: "Bearing Wear & Noise",
     1: "Vibration & Imbalance",
     2: "Mechanical Seal Leak",
     3: "Overheating",
     4: "Lubrication Issue",
     5: "Electrical Fault",
     6: "Corrosion & Erosion",
}

print("\nAuto-extracted top terms per cluster:")
print("-" * 55)
for cid in sorted(df_clean["cluster"].unique()):
    if cid == -1:
        continue
    terms = label_cluster(cid, df_clean, tfidf)
    name  = CLUSTER_NAMES.get(cid, f"Cluster {cid}")
    print(f"  [{cid}] {name}")
    print(f"       {', '.join(terms[:6])}")

df_clean["defect_cluster_name"] = df_clean["cluster"].map(
    lambda c: CLUSTER_NAMES.get(c, f"Cluster {c}")
)

# COMMAND ----------
# MAGIC %md ## 8 · Cluster quality — validation vs ground truth labels

# Map true labels → cluster (majority vote)
gt = df_clean["true_defect_label"]
pred = df_clean["cluster"].astype(str)

ari = adjusted_rand_score(gt, pred)
print(f"Adjusted Rand Index (ARI) vs ground truth : {ari:.4f}")
print("  (1.0 = perfect, 0.0 = random, negative = worse than random)\n")

# Confusion heatmap
ct = pd.crosstab(df_clean["true_defect_label"],
                 df_clean["defect_cluster_name"],
                 normalize="index").round(2)

fig, ax = plt.subplots(figsize=(12, 5))
sns.heatmap(ct, annot=True, fmt=".2f", cmap="Purples",
            linewidths=0.4, linecolor="white",
            cbar_kws={"shrink": 0.7}, ax=ax)
ax.set_xlabel("Predicted cluster", fontsize=11)
ax.set_ylabel("True defect label", fontsize=11)
ax.set_title("Cluster purity — true label vs predicted cluster (row-normalised)",
             fontsize=12, fontweight="500")
plt.xticks(rotation=30, ha="right", fontsize=9)
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/03_cluster_purity_heatmap.png", dpi=140)
plt.close()
print("Saved → 03_cluster_purity_heatmap.png")

# Cluster size bar
fig, ax = plt.subplots(figsize=(10, 4))
size_df = df_clean["defect_cluster_name"].value_counts()
colors = ["#534AB7" if "Other" not in n else "#888780" for n in size_df.index]
bars = ax.barh(size_df.index, size_df.values, color=colors, edgecolor="white", height=0.6)
for bar, v in zip(bars, size_df.values):
    ax.text(v + 3, bar.get_y() + bar.get_height()/2, str(v), va="center", fontsize=9)
ax.set_xlabel("Number of records", fontsize=11)
ax.set_title("Records per defect cluster", fontsize=12, fontweight="500")
ax.spines[["top","right"]].set_visible(False)
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/04_cluster_sizes.png", dpi=140)
plt.close()
print("Saved → 04_cluster_sizes.png")

# COMMAND ----------
# MAGIC %md ## 9 · 2-D UMAP projection for visual inspection
# MAGIC
# MAGIC We project the 64-dim embeddings to 2D so analysts can visually inspect
# MAGIC whether clusters are coherent and where the "Other" bucket sits.

try:
    from umap import UMAP
    print("Running UMAP projection …")
    reducer = UMAP(n_components=2, n_neighbors=20, min_dist=0.1,
                   metric="cosine", random_state=RANDOM_STATE)
    X_2d = reducer.fit_transform(embeddings)
    df_clean["umap_x"] = X_2d[:, 0]
    df_clean["umap_y"] = X_2d[:, 1]

    palette = ["#534AB7","#1D9E75","#D85A30","#D4537E","#378ADD","#639922","#BA7517","#888780"]
    cluster_ids = sorted(df_clean["cluster"].unique())

    fig, ax = plt.subplots(figsize=(10, 7))
    for i, cid in enumerate(cluster_ids):
        mask = df_clean["cluster"] == cid
        name = CLUSTER_NAMES.get(cid, f"Cluster {cid}")
        col  = palette[i % len(palette)]
        alpha = 0.35 if cid == -1 else 0.75
        sz    = 12   if cid == -1 else 18
        ax.scatter(df_clean.loc[mask, "umap_x"], df_clean.loc[mask, "umap_y"],
                   c=col, s=sz, alpha=alpha, label=name, linewidths=0)

    ax.set_title("UMAP projection of defect embeddings (coloured by cluster)",
                 fontsize=12, fontweight="500")
    ax.set_xlabel("UMAP-1"); ax.set_ylabel("UMAP-2")
    ax.legend(fontsize=8, markerscale=1.5, bbox_to_anchor=(1.01, 1), loc="upper left")
    ax.spines[["top","right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/05_umap_projection.png", dpi=140, bbox_inches="tight")
    plt.close()
    print("Saved → 05_umap_projection.png")
except ImportError:
    print("umap-learn not available, skipping projection.")

# COMMAND ----------
# MAGIC %md ## 10 · Write enriched feature table
# MAGIC
# MAGIC On Databricks, write back to Delta:
# MAGIC ```python
# MAGIC spark_df = spark.createDataFrame(df_features)
# MAGIC spark_df.write.format("delta").mode("overwrite") \
# MAGIC     .option("overwriteSchema","true") \
# MAGIC     .saveAsTable("maintenance.gold.defect_features")
# MAGIC ```

feature_cols = [
    "record_id","equipment_id","equipment_type","location","visit_date",
    "defect_description","true_defect_label",
    "cluster","defect_cluster_name",
    "severity","days_to_failure","repair_duration_hrs","downtime_hrs","parts_replaced",
    "quality_score",
    "data_quality_frequency","data_quality_freshness",
    "data_quality_completeness","data_quality_pertinence",
]

df_features = df_clean[feature_cols].copy()

# Aggregate cluster stats per equipment (used as ML features)
cluster_agg = (
    df_features.groupby("equipment_id")
    .agg(
        total_visits        = ("record_id",              "count"),
        distinct_defects    = ("cluster",                "nunique"),
        avg_quality_score   = ("quality_score",          "mean"),
        avg_repair_hrs      = ("repair_duration_hrs",    "mean"),
        avg_downtime_hrs    = ("downtime_hrs",           "mean"),
        pct_high_severity   = ("severity",               lambda x: (x=="High").mean()),
        last_visit_date     = ("visit_date",             "max"),
    )
    .reset_index()
    .round(3)
)

df_features.to_csv("/home/claude/predictive_maintenance/defect_features.csv", index=False)
cluster_agg.to_csv("/home/claude/predictive_maintenance/equipment_cluster_agg.csv", index=False)

print(f"Feature table saved   : defect_features.csv  ({len(df_features):,} rows)")
print(f"Equipment agg saved   : equipment_cluster_agg.csv  ({len(cluster_agg):,} rows)")
print(f"\nSample feature row:")
print(df_features.iloc[0].to_string())

# COMMAND ----------
# MAGIC %md ## 11 · Summary dashboard

print("\n" + "="*58)
print("  CLUSTERING SUMMARY")
print("="*58)
print(f"  Input records          : {len(df_raw):,}")
print(f"  After quality filter   : {len(df_clean):,}")
print(f"  Best k (silhouette)    : {best_k}")
print(f"  Final clusters         : {n_clusters_final}  + Other bucket")
print(f"  Min cluster size used  : {MIN_CLUSTER_SIZE}")
print(f"  ARI vs ground truth    : {ari:.4f}")
print(f"  Embedding dims         : {EMBED_DIM}")
print(f"  Plots saved to         : {OUTPUT_DIR}/")
print("="*58)
print("\nCluster membership:")
for cid, name in sorted(CLUSTER_NAMES.items()):
    n = (df_clean["cluster"] == cid).sum()
    if n > 0:
        pct = n / len(df_clean) * 100
        print(f"  [{cid:2d}] {name:<28} {n:4d}  ({pct:.1f}%)")

