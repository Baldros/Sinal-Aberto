"""Offline ingestion jobs.

These modules run OUTSIDE the MCP server (manually or on a schedule), never on a
user request. They download and distill public datasets into small prepared files
that the server reads read-only. Pure transform logic lives in dedicated modules
so it can be unit-tested without network access.
"""
