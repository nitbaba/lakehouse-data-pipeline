import dlt

from lakehouse.common.config import Settings
from lakehouse.ingestion.open_meteo import open_meteo_source


def build_pipeline(settings: Settings) -> dlt.Pipeline:
    return dlt.pipeline(
        pipeline_name="open_meteo_ingestion",
        destination=dlt.destinations.filesystem(bucket_url=settings.landing_path),
        dataset_name="open_meteo",
        progress="log",
    )


def run() -> None:
    settings = Settings.from_env()
    pipeline = build_pipeline(settings)
    load_info = pipeline.run(open_meteo_source())
    print(load_info)
    if load_info.has_failed_jobs:
        raise RuntimeError(f"dlt load had failed jobs: {load_info.load_packages}")


if __name__ == "__main__":
    run()
