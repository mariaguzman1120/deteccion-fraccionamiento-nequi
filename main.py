"""Entrypoint simple para ejecutar el pipeline del proyecto."""

from __future__ import annotations

import logging
from pathlib import Path

from python.utils import pipeline

RUN_REPORT_ONLY = True

INPUT_PATH = Path('data/sample_user_id_50.parquet')
OUTPUT_DIR = Path('data/outputs')

RESULT_PATH = Path('data/outputs/model_result.parquet')

REPORT_TITLE = 'Reporte de fraccionamiento transaccional'
TABLE_ROW_LIMIT = 50


def main() -> None:
    """Ejecuta el flujo completo o solo el HTML, segun la configuracion."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
    )

    if RUN_REPORT_ONLY:
        pipeline.run_report_pipeline(
            result_path=RESULT_PATH,
            title=REPORT_TITLE,
            table_row_limit=TABLE_ROW_LIMIT,
        )
    else:
        pipeline.run_detection_pipeline(
            input_path=INPUT_PATH,
            output_dir=OUTPUT_DIR,
            title=REPORT_TITLE,
            table_row_limit=TABLE_ROW_LIMIT,
        )


if __name__ == '__main__':
    main()
