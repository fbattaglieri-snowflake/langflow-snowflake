# Upstream Langflow 1.12.2; preserve upstream licenses in the image.
FROM langflowai/langflow@sha256:015cfee8f008f2e93dd703bbef76fc156e3ef1b246a8de18818d09658cb02546
USER root
RUN /app/.venv/bin/pip install --no-cache-dir --no-deps pgvector==0.5.0 \
    && /app/.venv/bin/python -c "import pgvector.sqlalchemy"
COPY --chmod=0755 docker/langflow/entrypoint.sh /usr/local/bin/persistent-entrypoint
ENTRYPOINT ["/usr/local/bin/persistent-entrypoint"]
CMD []