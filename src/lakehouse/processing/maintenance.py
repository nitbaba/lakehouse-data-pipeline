from datetime import datetime, timedelta, timezone

from lakehouse.processing.bronze import BRONZE_TABLE
from lakehouse.processing.gold import GOLD_TABLE
from lakehouse.processing.silver import SILVER_TABLE
from lakehouse.processing.spark_session import CATALOG, build_spark_session

MAINTAINED_TABLES = (BRONZE_TABLE, SILVER_TABLE, GOLD_TABLE)
SNAPSHOT_RETENTION_DAYS = 7
RETAIN_LAST_N_SNAPSHOTS = 5


def run() -> None:
    spark = build_spark_session("maintenance_weather")
    # Iceberg's expire_snapshots procedure needs a literal TIMESTAMP, not a
    # SQL expression like `current_timestamp() - INTERVAL 7 DAYS` — CALL
    # argument parsing doesn't accept arbitrary expressions there.
    older_than = datetime.now(timezone.utc) - timedelta(days=SNAPSHOT_RETENTION_DAYS)
    older_than_literal = older_than.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    for table in MAINTAINED_TABLES:
        # Iceberg system procedures take table identifiers relative to the
        # catalog they're called on (rest.system.*), without the catalog
        # prefix repeated in the argument.
        namespace_table = table.removeprefix(f"{CATALOG}.")

        print(f"Compacting {table}")
        spark.sql(f"CALL {CATALOG}.system.rewrite_data_files(table => '{namespace_table}')")

        print(f"Expiring old snapshots for {table}")
        spark.sql(
            f"CALL {CATALOG}.system.expire_snapshots("
            f"table => '{namespace_table}', "
            f"older_than => TIMESTAMP '{older_than_literal}', "
            f"retain_last => {RETAIN_LAST_N_SNAPSHOTS})"
        )


if __name__ == "__main__":
    run()
