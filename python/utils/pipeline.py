"""Utilidades para ejecutar el flujo completo del detector."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from . import cleaning, detection, io, reporting

logger = logging.getLogger(__name__)


def build_output_paths(
    output_dir: Path,
    file_stem: str,
) -> dict[str, Path]:
    """Define las rutas principales del pipeline.

    Args:
        output_dir: Directorio donde quedaran los artefactos.
        file_stem: Nombre base del archivo procesado.

    Returns:
        Diccionario con las rutas de salida.
    """
    repo_root = Path(__file__).resolve().parents[2]
    reporting_dir = repo_root / 'reporting'

    return {
        'alert_table_parquet': output_dir / f'{file_stem}_alert_table.parquet',
        'report_html': reporting_dir / f'{file_stem}_report.html',
    }


def run_report_pipeline(
    result_path: Path,
    title: str,
    table_row_limit: int = 250,
) -> Path:
    """Construye solo el HTML a partir de una tabla final existente.

    Args:
        result_path: Ruta de la tabla final del modelo.
        title: Titulo del reporte HTML.
        table_row_limit: Numero maximo de filas visibles en el HTML.

    Returns:
        Ruta del HTML generado.
    """
    if not result_path.exists():
        raise FileNotFoundError(f'No se encontro la tabla resultado: {result_path}')

    report_html_path = build_output_paths(
        output_dir=result_path.parent,
        file_stem=result_path.stem.replace('_alert_table', ''),
    )['report_html']

    report_html_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info('Cargando la tabla final del modelo')
    alert_table = pd.read_parquet(result_path)

    logger.info('Construyendo el HTML desde la tabla exportada')
    report_payload = reporting.build_report_payload_from_alert_table(
        dataset_name=result_path.name,
        generated_at=pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
        alert_table=alert_table,
    )

    html_content = reporting.render_html_report(
        report_payload=report_payload,
        title=title,
        table_row_limit=table_row_limit,
    )

    reporting.write_html_report(
        html_content=html_content,
        output_path=report_html_path,
    )

    logger.info('Reporte HTML: %s', report_html_path.resolve())

    return report_html_path


def run_detection_pipeline(
    input_path: Path,
    output_dir: Path,
    title: str,
    table_row_limit: int = 250,
) -> dict[str, Path]:
    """Ejecuta el flujo completo del notebook y aplica el modelo.

    Args:
        input_path: Ruta del parquet original.
        output_dir: Directorio donde se escribiran los artefactos.
        title: Titulo del reporte HTML.
        table_row_limit: Numero maximo de filas visibles en el HTML.

    Returns:
        Diccionario con las rutas generadas por el pipeline.
    """
    if not input_path.exists():
        raise FileNotFoundError(f'No se encontro el archivo: {input_path}')

    output_dir.mkdir(parents=True, exist_ok=True)

    entity_cols = detection.DEFAULT_ENTITY_COLS
    segment_cols = ['transaction_type']

    file_stem = input_path.stem
    output_paths = build_output_paths(
        output_dir=output_dir,
        file_stem=file_stem,
    )

    output_paths['report_html'].parent.mkdir(parents=True, exist_ok=True)

    logger.info('Cargando datos')
    raw_data = io.load_data(input_path)

    logger.info('Aplicando limpieza operativa')
    deduplicated_data = cleaning.deduplicate_transaction_ids(raw_data)
    required_clean_data = cleaning.drop_null_required_fields(deduplicated_data)
    clean_data = cleaning.drop_non_positive_transaction_amounts(required_clean_data)

    logger.info('Aplicando el modelo heuristico')

    alert_table = detection.build_scenario_detection_table(
        data=clean_data,
        entity_cols=entity_cols,
        segment_cols=segment_cols,
        window='24h',
    )

    logger.info('Exportando la salida final del modelo')
    alert_table.to_parquet(
        output_paths['alert_table_parquet'],
        index=False,
    )

    report_html_path = run_report_pipeline(
        result_path=output_paths['alert_table_parquet'],
        title=title,
        table_row_limit=table_row_limit,
    )
    output_paths['report_html'] = report_html_path

    logger.info('Pipeline finalizado')
    logger.info('Tabla final parquet: %s', output_paths['alert_table_parquet'].resolve())
    logger.info('Reporte HTML: %s', output_paths['report_html'].resolve())

    return output_paths
