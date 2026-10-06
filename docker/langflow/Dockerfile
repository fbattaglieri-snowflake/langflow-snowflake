# Upstream Langflow 1.12.2; preserve upstream licenses in the image.
FROM langflowai/langflow@sha256:4304bd9e67db00e72ab20d7a853abbc46d107901215b50a8298f4c4f45127eae
USER root
COPY docker/langflow/security-constraints.txt /tmp/security-constraints.txt
RUN /app/.venv/bin/pip install --no-cache-dir -r /tmp/security-constraints.txt \
    && /app/.venv/bin/python -c "import pgvector.sqlalchemy, jwt, pypdf, urllib3"
COPY --chmod=0755 docker/langflow/entrypoint.sh /usr/local/bin/persistent-entrypoint
ENTRYPOINT ["/usr/local/bin/persistent-entrypoint"]
CMD []