FROM apache/superset:6.1.0

USER root
COPY requirements.txt /requirements.txt
# The image's venv (/app/.venv) is uv-managed and has no `pip` binary of its
# own -- plain `pip install` resolves to a different, unrelated system
# Python and silently installs nowhere the app can see it. Target the venv
# explicitly via VIRTUAL_ENV, matching how the image's own
# docker-bootstrap.sh installs its optional Postgres driver.
RUN VIRTUAL_ENV=/app/.venv uv pip install --no-cache-dir -r /requirements.txt
COPY superset_config.py /app/pythonpath/superset_config.py
USER superset
