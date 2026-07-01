#!/usr/bin/env python
"""
Root entry point for the ETL pipeline.

A thin, friendly wrapper so the project can be run with a single command from
the project root:

    python run_pipeline.py            # regenerate data + full ETL
    python run_pipeline.py --no-generate

It simply delegates to ``etl.run`` (which can also be invoked as
``python -m etl.run``).
"""

from etl.run import main

if __name__ == "__main__":
    main()
