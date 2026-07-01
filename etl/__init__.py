"""
IT Helpdesk Analytics — ETL package.

An end-to-end Extract / Transform / Load pipeline for IT support-ticket data.
Each stage lives in its own module so the flow mirrors a real data-engineering
project:

    generate_data -> extract -> transform -> load

See ``etl/run.py`` (or ``run_pipeline.py`` at the project root) for the
orchestrated entry point.
"""

__version__ = "1.0.0"
