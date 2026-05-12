# Databricks notebook source
# MAGIC %md
# MAGIC # Setup — Load CSV Data into Delta Tables
# MAGIC
# MAGIC This notebook reads source CSVs from the Unity Catalog volume and creates
# MAGIC Delta tables for the predictive maintenance pipeline.

# COMMAND ----------
# MAGIC %md ## Configuration

# COMMAND ----------

CATALOG = "serverless_stable_3n0ihb_catalog"
SCHEMA = "msc_cargo_predictive_maintenance"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data"

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"Catalog : {CATALOG}")
print(f"Schema  : {SCHEMA}")
print(f"Volume  : {VOLUME_PATH}")

# COMMAND ----------
# MAGIC %md ## Load equipment_master

# COMMAND ----------

df_equipment = (
    spark.read.format("csv")
    .option("header", "true")
    .option("inferSchema", "true")
    .load(f"{VOLUME_PATH}/equipment_master.csv")
)

df_equipment.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("equipment_master")

print(f"equipment_master: {df_equipment.count()} rows")
df_equipment.printSchema()

# COMMAND ----------
# MAGIC %md ## Load work_orders

# COMMAND ----------

df_work_orders = (
    spark.read.format("csv")
    .option("header", "true")
    .option("inferSchema", "true")
    .load(f"{VOLUME_PATH}/work_orders.csv")
)

df_work_orders.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("work_orders")

print(f"work_orders: {df_work_orders.count()} rows")
df_work_orders.printSchema()

# COMMAND ----------
# MAGIC %md ## Verify

# COMMAND ----------

# MAGIC %sql
# MAGIC SHOW TABLES;

# COMMAND ----------

print("Setup complete.")
print(f"  equipment_master : {spark.table('equipment_master').count()} rows")
print(f"  work_orders      : {spark.table('work_orders').count()} rows")
