"""Utilidades para construir un reporte HTML del detector."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from . import cleaning, detection, eda

SCENARIO_LABELS = {
    'scenario_burst_similar': 'ráfaga con montos similares',
    'scenario_burst_anomalous': 'ráfaga anómala frente al histórico',
    'scenario_material_amount': 'monto agregado material',
    'scenario_destination_dispersion': 'dispersión entre sedes o destinos',
}

ALERT_LEVEL_PRIORITY = {
    'alta': 0,
    'media': 1,
    'pre_alerta': 2,
    'sin_alerta': 3,
}

REPORT_STYLES = """
<style>
  :root {
    --bg: #ece7f5;
    --panel: rgba(255, 255, 255, 0.96);
    --ink: #200020;
    --muted: #65556f;
    --line: rgba(32, 0, 32, 0.10);
    --accent: #da0081;
    --accent-2: #2b0d2b;
    --warning: #f59e0b;
    --success: #0f8b6d;
    --danger: #da0081;
    --shadow: 0 18px 48px rgba(32, 0, 32, 0.08);
    --radius: 22px;
  }

  * {
    box-sizing: border-box;
  }

  body {
    margin: 0;
    font-family: "Aptos", "Segoe UI", "Trebuchet MS", sans-serif;
    color: var(--ink);
    background:
      radial-gradient(circle at top left, rgba(218, 0, 129, 0.10), transparent 30%),
      radial-gradient(circle at top right, rgba(43, 13, 43, 0.10), transparent 26%),
      linear-gradient(180deg, #f8f5fb 0%, #ece7f5 100%);
  }

  .page-shell {
    max-width: 1420px;
    margin: 0 auto;
    padding: 40px 24px 56px;
  }

  .hero {
    display: grid;
    grid-template-columns: minmax(0, 1.8fr) minmax(320px, 1fr);
    gap: 20px;
    margin-bottom: 24px;
  }

  .hero-card,
  .panel {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    animation: rise 560ms ease both;
  }

  .hero-card {
    padding: 30px;
  }

  .hero-brand {
    display: inline-flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 12px;
  }

  .hero-logo {
    display: block;
    width: 132px;
    max-width: 100%;
    height: auto;
  }

  .eyebrow {
    margin: 0 0 10px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--accent);
    font-size: 12px;
    font-weight: 700;
  }

  h1 {
    margin: 0;
    font-family: "Cambria", "Times New Roman", serif;
    font-size: clamp(32px, 4vw, 48px);
    line-height: 1.02;
  }

  .hero-lead {
    margin: 16px 0 18px;
    max-width: 68ch;
    color: var(--muted);
    font-size: 16px;
    line-height: 1.65;
  }

  .meta-row,
  .bullet-list {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .meta-pill {
    display: inline-flex;
    align-items: center;
    padding: 8px 12px;
    border-radius: 999px;
    background: rgba(218, 0, 129, 0.08);
    color: var(--accent-2);
    font-size: 13px;
    font-weight: 600;
  }

  .bullet-list {
    gap: 12px;
    padding: 0;
    margin: 16px 0 0;
    list-style: none;
  }

  .bullet-list li {
    width: 100%;
    padding: 12px 14px;
    border-radius: 16px;
    background: rgba(218, 0, 129, 0.08);
    color: var(--accent-2);
    line-height: 1.45;
  }

  .metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin: 0 0 28px;
  }

  .metric-card {
    padding: 20px;
  }

  .metric-card-head {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .metric-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    border-radius: 12px;
    font-size: 18px;
    background: rgba(32, 0, 32, 0.06);
  }

  .metric-context {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
  }

  .metric-label {
    color: var(--muted);
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .metric-value {
    margin: 10px 0 6px;
    font-size: 30px;
    font-weight: 800;
    line-height: 1.05;
  }

  .metric-hint {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.5;
  }

  .metric-card.tone-neutral {
    border-top: 4px solid rgba(32, 0, 32, 0.12);
  }

  .metric-card.tone-accent {
    border-top: 4px solid var(--accent);
  }

  .metric-card.tone-warning {
    border-top: 4px solid var(--warning);
  }

  .metric-card.tone-high {
    border-top: 4px solid var(--danger);
  }

  .metric-card.tone-success {
    border-top: 4px solid var(--success);
  }

  .metric-card.tone-accent .metric-icon,
  .metric-card.tone-high .metric-icon,
  .metric-card.tone-warning .metric-icon,
  .metric-card.tone-success .metric-icon {
    color: var(--ink);
  }

  .section {
    margin-top: 28px;
  }

  .section-kicker {
    margin: 0 0 6px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--accent);
    font-size: 12px;
    font-weight: 800;
  }

  .section-head {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: end;
    margin-bottom: 16px;
  }

  .section-head h2 {
    margin: 0 0 4px;
    font-family: "Cambria", "Times New Roman", serif;
    font-size: 28px;
  }

  .section-head p {
    margin: 0;
    color: var(--muted);
    line-height: 1.5;
  }

  .grid-two {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
  }

  .grid-split {
    display: grid;
    grid-template-columns: minmax(260px, 0.8fr) minmax(0, 1.6fr);
    gap: 16px;
  }

  .panel {
    padding: 20px;
  }

  .panel h3 {
    margin: 0 0 6px;
    font-size: 18px;
  }

  .panel p {
    margin: 0 0 14px;
    color: var(--muted);
    line-height: 1.5;
  }

  .story-grid {
    display: grid;
    gap: 12px;
  }

  .story-card {
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr);
    gap: 12px;
    padding: 14px;
    border-radius: 18px;
    background: rgba(236, 231, 245, 0.58);
    border: 1px solid rgba(32, 0, 32, 0.06);
  }

  .story-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 42px;
    height: 42px;
    border-radius: 14px;
    font-size: 20px;
    background: rgba(218, 0, 129, 0.10);
  }

  .story-title {
    margin: 0;
    font-size: 13px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
  }

  .story-value {
    margin: 4px 0 6px;
    font-size: 18px;
    font-weight: 800;
    color: var(--accent-2);
  }

  .story-hint {
    margin: 0;
    color: var(--muted);
    line-height: 1.5;
    font-size: 14px;
  }

  .progress-list,
  .rank-list {
    display: grid;
    gap: 14px;
  }

  .progress-item,
  .rank-item {
    padding: 12px 14px;
    border-radius: 18px;
    background: rgba(236, 231, 245, 0.44);
    border: 1px solid rgba(32, 0, 32, 0.06);
  }

  .progress-head,
  .rank-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 8px;
  }

  .progress-label,
  .rank-label-wrap {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .progress-value,
  .rank-value {
    font-weight: 800;
    color: var(--accent-2);
    white-space: nowrap;
  }

  .rank-label {
    font-size: 14px;
    font-weight: 700;
    color: var(--ink);
  }

  .progress-track,
  .rank-track {
    width: 100%;
    height: 12px;
    overflow: hidden;
    border-radius: 999px;
    background: rgba(32, 0, 32, 0.08);
  }

  .progress-fill,
  .rank-fill {
    height: 100%;
    border-radius: 999px;
    min-width: 8px;
    background: linear-gradient(90deg, rgba(218, 0, 129, 0.88), rgba(43, 13, 43, 0.82));
  }

  .progress-fill.tone-warning,
  .rank-fill.tone-warning {
    background: linear-gradient(90deg, rgba(245, 158, 11, 0.95), rgba(218, 0, 129, 0.85));
  }

  .progress-fill.tone-high,
  .rank-fill.tone-high {
    background: linear-gradient(90deg, rgba(218, 0, 129, 0.95), rgba(128, 0, 64, 0.88));
  }

  .progress-fill.tone-success,
  .rank-fill.tone-success {
    background: linear-gradient(90deg, rgba(15, 139, 109, 0.92), rgba(32, 0, 32, 0.82));
  }

  .progress-note,
  .rank-note {
    margin-top: 8px;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.45;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }

  thead th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: rgba(236, 231, 245, 0.98);
    color: var(--accent-2);
    text-align: left;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 1px solid var(--line);
    padding: 12px 10px;
  }

  tbody td {
    padding: 11px 10px;
    border-bottom: 1px solid var(--line);
    vertical-align: top;
  }

  tbody tr:last-child td {
    border-bottom: none;
  }

  tbody tr:hover {
    background: rgba(218, 0, 129, 0.05);
  }

  .table-wrap {
    max-height: 380px;
    overflow: auto;
    border-radius: 18px;
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.82);
  }

  .filters {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }

  .filter-field {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .filter-field label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    font-weight: 700;
  }

  .filter-field input,
  .filter-field select,
  .filter-field button {
    min-height: 44px;
    padding: 10px 12px;
    border-radius: 14px;
    border: 1px solid rgba(32, 0, 32, 0.12);
    background: rgba(255, 255, 255, 0.9);
    color: var(--ink);
    font: inherit;
  }

  .filter-field button {
    cursor: pointer;
    font-weight: 700;
    background: linear-gradient(135deg, rgba(218, 0, 129, 0.14), rgba(43, 13, 43, 0.12));
  }

  .summary-line {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 14px;
  }

  .summary-pill {
    padding: 8px 10px;
    border-radius: 999px;
    background: rgba(236, 231, 245, 0.92);
    color: var(--accent-2);
    font-size: 13px;
    font-weight: 600;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .chip.alta {
    background: rgba(218, 0, 129, 0.14);
    color: var(--danger);
  }

  .chip.media {
    background: rgba(245, 158, 11, 0.14);
    color: var(--warning);
  }

  .chip.pre_alerta {
    background: rgba(43, 13, 43, 0.08);
    color: var(--accent-2);
  }

  .chip.sin_alerta {
    background: rgba(15, 139, 109, 0.10);
    color: var(--success);
  }

  .bar-chart {
    display: flex;
    align-items: end;
    gap: 10px;
    min-height: 280px;
    padding: 16px 14px 10px;
    overflow-x: auto;
    overflow-y: hidden;
    border-radius: 18px;
    background:
      linear-gradient(180deg, rgba(218, 0, 129, 0.04), transparent 50%),
      rgba(255, 255, 255, 0.82);
    border: 1px solid var(--line);
  }

  .bar-item {
    flex: 0 0 34px;
    display: grid;
    grid-template-rows: 22px 180px 20px;
    gap: 8px;
    align-items: end;
  }

  .bar-track {
    width: 100%;
    height: 180px;
    display: flex;
    align-items: end;
    border-radius: 14px;
    background:
      linear-gradient(180deg, rgba(32, 0, 32, 0.04), rgba(32, 0, 32, 0.01));
    border: 1px solid rgba(32, 0, 32, 0.06);
    padding: 4px;
  }

  .bar {
    height: 100%;
    width: 100%;
    min-height: 8px;
    border-radius: 10px 10px 6px 6px;
    background: linear-gradient(180deg, rgba(218, 0, 129, 0.88), rgba(43, 13, 43, 0.82));
    box-shadow: 0 8px 18px rgba(218, 0, 129, 0.12);
  }

  .bar-label {
    font-size: 11px;
    color: var(--muted);
    font-weight: 700;
    letter-spacing: 0.02em;
    text-align: center;
  }

  .bar-value {
    font-size: 11px;
    color: var(--accent-2);
    font-weight: 700;
    text-align: center;
  }

  .empty-state {
    padding: 28px 16px;
    color: var(--muted);
    text-align: center;
    border-radius: 18px;
    border: 1px dashed rgba(32, 0, 32, 0.18);
    background: rgba(255, 255, 255, 0.68);
  }

  .note {
    margin-top: 12px;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.5;
  }

  @keyframes rise {
    from {
      opacity: 0;
      transform: translateY(12px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 980px) {
    .hero,
    .grid-split {
      grid-template-columns: 1fr;
    }

    .page-shell {
      padding: 24px 16px 40px;
    }

    .bar-item {
      flex-basis: 30px;
      grid-template-rows: 20px 160px 18px;
    }
  }
</style>
"""

REPORT_SCRIPT = """
<script>
  const reportData = JSON.parse(document.getElementById('report-data').textContent);
  const tableRowLimit = reportData.meta.table_row_limit;

  const numberFormatter = new Intl.NumberFormat('es-CO', {
    maximumFractionDigits: 0,
  });

  const decimalFormatter = new Intl.NumberFormat('es-CO', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  function formatInteger(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return 'NA';
    }

    return numberFormatter.format(Number(value));
  }

  function formatDecimal(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return 'NA';
    }

    return decimalFormatter.format(Number(value));
  }

  function formatCurrency(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return 'NA';
    }

    return '$ ' + numberFormatter.format(Number(value));
  }

  function escapeHtml(value) {
    if (value === null || value === undefined) {
      return '';
    }

    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function buildSelectOptions(selectId, values) {
    const select = document.getElementById(selectId);
    const uniqueValues = Array.from(new Set(values)).filter(Boolean);

    uniqueValues.sort((left, right) => String(left).localeCompare(String(right)));

    uniqueValues.forEach((value) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
  }

  function normalizeText(value) {
    if (value === null || value === undefined) {
      return '';
    }

    return String(value).toLowerCase();
  }

  function filterCases() {
    const alertLevel = document.getElementById('alert-level-filter').value;
    const transactionType = document.getElementById('transaction-type-filter').value;
    const startDate = document.getElementById('start-date-filter').value;
    const endDate = document.getElementById('end-date-filter').value;
    const search = normalizeText(document.getElementById('search-filter').value.trim());

    return reportData.alert_cases.filter((row) => {
      if (alertLevel !== 'all' && row.alert_level !== alertLevel) {
        return false;
      }

      if (transactionType !== 'all' && row.transaction_type !== transactionType) {
        return false;
      }

      if (startDate && row.transaction_day < startDate) {
        return false;
      }

      if (endDate && row.transaction_day > endDate) {
        return false;
      }

      if (!search) {
        return true;
      }

      const haystack = [
        row.user_id,
        row.account_number,
        row.top_merchant_id,
        row.top_subsidiary,
        row.reason,
      ];

      return haystack.some((value) => normalizeText(value).includes(search));
    });
  }

  function renderDynamicMetrics(rows) {
    const container = document.getElementById('filtered-metrics');

    if (!rows.length) {
      container.innerHTML = `
        <div class="panel metric-card tone-neutral">
          <div class="metric-card-head">
            <span class="metric-icon">🔎</span>
            <span class="metric-context">Subconjunto filtrado</span>
          </div>
          <div class="metric-label">Sin resultados</div>
          <div class="metric-value">0</div>
          <div class="metric-hint">Ajusta los filtros para volver a ver casos.</div>
        </div>
      `;
      return;
    }

    const totalAmount = rows.reduce((acc, row) => acc + Number(row.amount_24h || 0), 0);
    const totalTransactions = rows.reduce((acc, row) => acc + Number(row.tx_count_24h || 0), 0);
    const uniqueUsers = new Set(rows.map((row) => row.user_id)).size;
    const maxScenarioCount = rows.reduce((acc, row) => Math.max(acc, Number(row.scenario_count || 0)), 0);
    const highAlerts = rows.filter((row) => row.alert_level === 'alta').length;

    const cards = [
      {
        icon: '🔎',
        context: 'Subconjunto filtrado',
        label: 'Casos visibles',
        value: formatInteger(rows.length),
        hint: 'Ventanas sospechosas que pasan los filtros.',
        tone: 'neutral',
      },
      {
        icon: '💰',
        context: 'Impacto filtrado',
        label: 'Monto 24h visible',
        value: formatCurrency(totalAmount),
        hint: 'Suma acumulada de monto en las ventanas visibles.',
        tone: 'accent',
      },
      {
        icon: '👤',
        context: 'Cobertura filtrada',
        label: 'Usuarios únicos',
        value: formatInteger(uniqueUsers),
        hint: 'Usuarios distintos dentro del subconjunto filtrado.',
        tone: 'neutral',
      },
      {
        icon: '📈',
        context: 'Intensidad media',
        label: 'Promedio tx por caso',
        value: formatDecimal(totalTransactions / rows.length),
        hint: 'Frecuencia media de transacciones por ventana.',
        tone: 'warning',
      },
      {
        icon: '🚨',
        context: 'Escalamiento filtrado',
        label: 'Alertas altas',
        value: formatInteger(highAlerts),
        hint: 'Casos con tres o más escenarios activados.',
        tone: 'high',
      },
      {
        icon: '🧠',
        context: 'Profundidad máxima',
        label: 'Máx. escenarios',
        value: formatInteger(maxScenarioCount),
        hint: 'Mayor conteo de escenarios activos en una sola ventana.',
        tone: 'accent',
      },
    ];

    container.innerHTML = cards.map((card) => {
      return `
        <div class="panel metric-card tone-${escapeHtml(card.tone)}">
          <div class="metric-card-head">
            <span class="metric-icon">${escapeHtml(card.icon)}</span>
            <span class="metric-context">${escapeHtml(card.context)}</span>
          </div>
          <div class="metric-label">${escapeHtml(card.label)}</div>
          <div class="metric-value">${escapeHtml(card.value)}</div>
          <div class="metric-hint">${escapeHtml(card.hint)}</div>
        </div>
      `;
    }).join('');
  }

  function renderBarChart(rows) {
    const container = document.getElementById('filtered-bar-chart');
    const grouped = {};

    rows.forEach((row) => {
      grouped[row.transaction_day] = (grouped[row.transaction_day] || 0) + 1;
    });

    const entries = Object.entries(grouped).sort((left, right) => left[0].localeCompare(right[0]));

    if (!entries.length) {
      container.innerHTML = '<div class="empty-state">No hay casos para construir la serie diaria con los filtros actuales.</div>';
      return;
    }

    const maxValue = Math.max(...entries.map((entry) => entry[1]), 1);

    container.innerHTML = entries.map(([day, value]) => {
      const height = Math.max(8, Math.round((value / maxValue) * 170));
      const shortDay = day.slice(5);

      return `
        <div class="bar-item" title="${escapeHtml(day)}: ${formatInteger(value)} casos">
          <div class="bar-value">${formatInteger(value)}</div>
          <div class="bar-track">
            <div class="bar" style="height: ${height}px;"></div>
          </div>
          <div class="bar-label">${escapeHtml(shortDay)}</div>
        </div>
      `;
    }).join('');
  }

  function renderTopMerchants(rows) {
    const container = document.getElementById('filtered-merchant-table');

    if (!rows.length) {
      container.innerHTML = '<div class="empty-state">Sin casos visibles para resumir por merchant.</div>';
      return;
    }

    const grouped = {};

    rows.forEach((row) => {
      const merchant = row.top_merchant_id || 'NA';

      if (!grouped[merchant]) {
        grouped[merchant] = {
          merchant: merchant,
          n_cases: 0,
          total_amount: 0,
          high_alerts: 0,
        };
      }

      grouped[merchant].n_cases += 1;
      grouped[merchant].total_amount += Number(row.amount_24h || 0);

      if (row.alert_level === 'alta') {
        grouped[merchant].high_alerts += 1;
      }
    });

    const topRows = Object.values(grouped)
      .sort((left, right) => {
        if (right.n_cases !== left.n_cases) {
          return right.n_cases - left.n_cases;
        }

        return right.total_amount - left.total_amount;
      })
      .slice(0, 8);

    const tableHtml = `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Merchant</th>
              <th>Casos</th>
              <th>Monto 24h</th>
              <th>Altas</th>
            </tr>
          </thead>
          <tbody>
            ${topRows.map((row) => `
              <tr>
                <td>${escapeHtml(row.merchant)}</td>
                <td>${formatInteger(row.n_cases)}</td>
                <td>${formatCurrency(row.total_amount)}</td>
                <td>${formatInteger(row.high_alerts)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;

    container.innerHTML = tableHtml;
  }

  function renderCasesTable(rows) {
    const summary = document.getElementById('filtered-table-summary');
    const body = document.getElementById('filtered-cases-body');

    if (!rows.length) {
      summary.innerHTML = '<span class="summary-pill">0 casos visibles</span>';
      body.innerHTML = '<tr><td colspan="10"><div class="empty-state">No hay filas para mostrar con los filtros actuales.</div></td></tr>';
      return;
    }

    const renderedRows = rows.slice(0, tableRowLimit);
    summary.innerHTML = `
      <span class="summary-pill">${formatInteger(rows.length)} casos visibles</span>
      <span class="summary-pill">Mostrando ${formatInteger(renderedRows.length)} filas</span>
      <span class="summary-pill">Límite visual ${formatInteger(tableRowLimit)}</span>
    `;

    body.innerHTML = renderedRows.map((row) => {
      return `
        <tr>
          <td>${escapeHtml(row.transaction_day)}</td>
          <td><span class="chip ${escapeHtml(row.alert_level)}">${escapeHtml(row.alert_level)}</span></td>
          <td>${escapeHtml(row.transaction_type)}</td>
          <td>${escapeHtml(row.user_id)}</td>
          <td>${escapeHtml(row.account_number)}</td>
          <td>${escapeHtml(row.top_merchant_id)}</td>
          <td>${escapeHtml(row.top_subsidiary)}</td>
          <td>${formatInteger(row.tx_count_24h)}</td>
          <td>${formatCurrency(row.amount_24h)}</td>
          <td>${escapeHtml(row.reason)}</td>
        </tr>
      `;
    }).join('');
  }

  function refreshInteractiveSection() {
    const rows = filterCases();
    renderDynamicMetrics(rows);
    renderBarChart(rows);
    renderTopMerchants(rows);
    renderCasesTable(rows);
  }

  function resetFilters() {
    document.getElementById('alert-level-filter').value = 'all';
    document.getElementById('transaction-type-filter').value = 'all';
    document.getElementById('start-date-filter').value = '';
    document.getElementById('end-date-filter').value = '';
    document.getElementById('search-filter').value = '';
    refreshInteractiveSection();
  }

  function init() {
    buildSelectOptions('alert-level-filter', reportData.filter_options.alert_levels);
    buildSelectOptions('transaction-type-filter', reportData.filter_options.transaction_types);

    [
      'alert-level-filter',
      'transaction-type-filter',
      'start-date-filter',
      'end-date-filter',
      'search-filter',
    ].forEach((elementId) => {
      document.getElementById(elementId).addEventListener('input', refreshInteractiveSection);
      document.getElementById(elementId).addEventListener('change', refreshInteractiveSection);
    });

    document.getElementById('reset-filters').addEventListener('click', resetFilters);
    refreshInteractiveSection();
  }

  window.addEventListener('DOMContentLoaded', init);
</script>
"""


def build_cleaning_summary(
    raw_data: pd.DataFrame,
    deduplicated_data: pd.DataFrame,
    required_clean_data: pd.DataFrame,
    clean_data: pd.DataFrame,
) -> pd.DataFrame:
    """Construye un resumen corto de las etapas de limpieza.

    Args:
        raw_data: DataFrame cargado desde el parquet.
        deduplicated_data: DataFrame tras eliminar duplicados seguros.
        required_clean_data: DataFrame sin nulos en campos obligatorios.
        clean_data: DataFrame final tras validar montos.

    Returns:
        Tabla con filas removidas y remanentes por etapa.
    """
    raw_rows = len(raw_data)
    deduplicated_rows = len(deduplicated_data)
    required_clean_rows = len(required_clean_data)
    clean_rows = len(clean_data)

    summary_rows = [
        {
            'step': 'entrada cruda',
            'rows_removed': 0,
            'rows_remaining': raw_rows,
            'pct_removed_step': 0.0,
            'pct_remaining_vs_raw': 100.0,
        },
        {
            'step': 'deduplicacion de _id',
            'rows_removed': raw_rows - deduplicated_rows,
            'rows_remaining': deduplicated_rows,
            'pct_removed_step': _safe_pct(
                raw_rows - deduplicated_rows,
                raw_rows,
            ),
            'pct_remaining_vs_raw': _safe_pct(
                deduplicated_rows,
                raw_rows,
            ),
        },
        {
            'step': 'nulos en campos obligatorios',
            'rows_removed': deduplicated_rows - required_clean_rows,
            'rows_remaining': required_clean_rows,
            'pct_removed_step': _safe_pct(
                deduplicated_rows - required_clean_rows,
                deduplicated_rows,
            ),
            'pct_remaining_vs_raw': _safe_pct(
                required_clean_rows,
                raw_rows,
            ),
        },
        {
            'step': 'montos no positivos',
            'rows_removed': required_clean_rows - clean_rows,
            'rows_remaining': clean_rows,
            'pct_removed_step': _safe_pct(
                required_clean_rows - clean_rows,
                required_clean_rows,
            ),
            'pct_remaining_vs_raw': _safe_pct(
                clean_rows,
                raw_rows,
            ),
        },
    ]

    summary_df = pd.DataFrame(summary_rows)

    return summary_df


def build_alert_cases_table(alert_table: pd.DataFrame) -> pd.DataFrame:
    """Construye la tabla de casos sospechosos para el HTML.

    Args:
        alert_table: Tabla final de escenarios del detector.

    Returns:
        Tabla reducida y ordenada para consumo del reporte.
    """
    case_mask = alert_table['scenario_count'] > 0

    source_df = alert_table.loc[
        case_mask,
        [
            'transaction_day',
            'window_start',
            'window_end',
            'user_id',
            'account_number',
            'transaction_type',
            'top_merchant_id',
            'top_subsidiary',
            'tx_count_24h',
            'amount_24h',
            'avg_amount_24h',
            'cv_amount_24h',
            'scenario_count',
            'alert_level',
            *SCENARIO_LABELS.keys(),
        ],
    ]

    alert_cases = source_df.reset_index(drop=True)
    alert_cases['reason'] = source_df.apply(_build_alert_reason, axis=1).reset_index(
        drop=True
    )

    text_cols = [
        'user_id',
        'account_number',
        'transaction_type',
        'top_merchant_id',
        'top_subsidiary',
        'alert_level',
        'reason',
    ]

    for col in text_cols:
        alert_cases[col] = alert_cases[col].fillna('NA')
        alert_cases[col] = alert_cases[col].astype(str)

    alert_cases['level_priority'] = (
        alert_cases['alert_level'].map(ALERT_LEVEL_PRIORITY).fillna(9)
    )

    alert_cases = alert_cases.sort_values(
        ['level_priority', 'scenario_count', 'amount_24h', 'tx_count_24h'],
        ascending=[True, False, False, False],
    )

    alert_cases = alert_cases.reset_index(drop=True)
    alert_cases = alert_cases.drop(columns=['level_priority'])

    return alert_cases


def build_top_alert_merchants(alert_cases: pd.DataFrame) -> pd.DataFrame:
    """Resume los merchants dominantes entre los casos sospechosos.

    Args:
        alert_cases: Tabla reducida de casos sospechosos.

    Returns:
        DataFrame con top merchants por numero de casos.
    """
    if alert_cases.empty:
        return pd.DataFrame(
            columns=[
                'top_merchant_id',
                'n_cases',
                'pct_cases',
                'high_alert_cases',
                'total_amount_24h',
            ]
        )

    merchant_df = alert_cases.loc[
        :,
        [
            'top_merchant_id',
            'alert_level',
            'amount_24h',
        ],
    ]

    merchant_df = merchant_df.groupby(
        'top_merchant_id',
        as_index=False,
    )

    merchant_df = merchant_df.agg(
        n_cases=('top_merchant_id', 'size'),
        high_alert_cases=('alert_level', lambda values: values.eq('alta').sum()),
        total_amount_24h=('amount_24h', 'sum'),
    )
    merchant_df['pct_cases'] = 0.0
    merchant_df['pct_cases'] = (
        100 * merchant_df['n_cases'] / len(alert_cases)
    )

    merchant_df = merchant_df.sort_values(
        ['n_cases', 'high_alert_cases', 'total_amount_24h'],
        ascending=[False, False, False],
    )

    merchant_df = merchant_df.head(10)
    merchant_df = merchant_df.reset_index(drop=True)

    return merchant_df


def build_alert_type_summary(alert_cases: pd.DataFrame) -> pd.DataFrame:
    """Resume los casos sospechosos por tipo de transaccion.

    Args:
        alert_cases: Tabla reducida de casos sospechosos.

    Returns:
        Tabla agregada por `transaction_type`.
    """
    if alert_cases.empty:
        return pd.DataFrame(
            columns=[
                'transaction_type',
                'n_cases',
                'pct_cases',
                'high_alert_cases',
                'total_amount_24h',
                'avg_scenario_count',
            ]
        )

    type_summary_df = alert_cases.groupby(
        'transaction_type',
        as_index=False,
    )

    type_summary_df = type_summary_df.agg(
        n_cases=('transaction_type', 'size'),
        high_alert_cases=('alert_level', lambda values: values.eq('alta').sum()),
        total_amount_24h=('amount_24h', 'sum'),
        avg_scenario_count=('scenario_count', 'mean'),
    )
    type_summary_df['pct_cases'] = 0.0
    type_summary_df['pct_cases'] = (
        100 * type_summary_df['n_cases'] / len(alert_cases)
    )

    type_summary_df = type_summary_df.sort_values(
        ['n_cases', 'total_amount_24h'],
        ascending=[False, False],
    )

    type_summary_df = type_summary_df.reset_index(drop=True)

    return type_summary_df


def build_priority_funnel(
    alert_table: pd.DataFrame,
    alert_cases: pd.DataFrame,
) -> pd.DataFrame:
    """Construye un embudo operativo corto para el reporte.

    Args:
        alert_table: Tabla final del detector.
        alert_cases: Casos con al menos un escenario activo.

    Returns:
        Tabla corta con etapas, volumen y proporcion sobre el total evaluado.
    """
    total_windows = len(alert_table)
    suspicious_cases = len(alert_cases)
    actionable_cases = int(alert_table['is_alert'].sum())
    high_alert_cases = int(alert_table['alert_level'].eq('alta').sum())

    funnel_rows = [
        {
            'icon': '🗂️',
            'label': 'Ventanas evaluadas',
            'value': total_windows,
            'pct_total': _safe_pct(total_windows, total_windows),
            'hint': 'Base completa consolidada por entidad y día.',
            'tone': 'neutral',
        },
        {
            'icon': '⚠️',
            'label': 'Casos con señal',
            'value': suspicious_cases,
            'pct_total': _safe_pct(suspicious_cases, total_windows),
            'hint': 'Ventanas con al menos un escenario activo.',
            'tone': 'warning',
        },
        {
            'icon': '🎯',
            'label': 'Casos accionables',
            'value': actionable_cases,
            'pct_total': _safe_pct(actionable_cases, total_windows),
            'hint': 'Casos en nivel media o alta para revisión.',
            'tone': 'accent',
        },
        {
            'icon': '🚨',
            'label': 'Alertas altas',
            'value': high_alert_cases,
            'pct_total': _safe_pct(high_alert_cases, total_windows),
            'hint': 'Casos con tres o más escenarios activos.',
            'tone': 'high',
        },
    ]

    funnel_df = pd.DataFrame(funnel_rows)

    return funnel_df


def build_scenario_importance(alert_cases: pd.DataFrame) -> pd.DataFrame:
    """Resume que escenarios explican la mayor parte de los casos.

    Args:
        alert_cases: Tabla reducida de casos sospechosos.

    Returns:
        Tabla con frecuencia e impacto de cada escenario.
    """
    if alert_cases.empty:
        return pd.DataFrame(
            columns=[
                'scenario_label',
                'n_cases',
                'pct_cases',
                'avg_amount_24h',
                'icon',
                'tone',
            ]
        )

    rows = []

    for col, label in SCENARIO_LABELS.items():
        scenario_mask = alert_cases[col] == 1
        scenario_cases = int(scenario_mask.sum())
        avg_amount = 0.0

        if scenario_cases > 0:
            avg_amount = float(alert_cases.loc[scenario_mask, 'amount_24h'].mean())

        rows.append(
            {
                'scenario_label': label,
                'n_cases': scenario_cases,
                'pct_cases': _safe_pct(scenario_cases, len(alert_cases)),
                'avg_amount_24h': avg_amount,
                'icon': '🧠',
                'tone': 'accent',
            }
        )

    scenario_df = pd.DataFrame(rows)
    scenario_df = scenario_df.sort_values(
        ['n_cases', 'avg_amount_24h'],
        ascending=[False, False],
    )
    scenario_df = scenario_df.reset_index(drop=True)

    return scenario_df


def build_scenario_depth_summary(alert_cases: pd.DataFrame) -> pd.DataFrame:
    """Resume la profundidad de escenarios activados por caso.

    Args:
        alert_cases: Tabla reducida de casos sospechosos.

    Returns:
        Tabla con distribucion por numero de escenarios activos.
    """
    if alert_cases.empty:
        return pd.DataFrame(
            columns=[
                'scenario_bucket',
                'n_cases',
                'pct_cases',
                'avg_amount_24h',
                'icon',
                'tone',
            ]
        )

    depth_df = alert_cases.groupby(
        'scenario_count',
        as_index=False,
    )

    depth_df = depth_df.agg(
        n_cases=('scenario_count', 'size'),
        avg_amount_24h=('amount_24h', 'mean'),
    )

    depth_df['pct_cases'] = 0.0
    depth_df['pct_cases'] = (
        100 * depth_df['n_cases'] / len(alert_cases)
    )
    depth_df['scenario_bucket'] = depth_df['scenario_count'].astype(int).astype(str)
    depth_df['scenario_bucket'] = depth_df['scenario_bucket'] + ' escenario'
    depth_df.loc[
        depth_df['scenario_count'] != 1,
        'scenario_bucket',
    ] = depth_df.loc[
        depth_df['scenario_count'] != 1,
        'scenario_bucket',
    ] + 's'

    depth_df['icon'] = '⚙️'
    depth_df['tone'] = 'neutral'
    depth_df.loc[depth_df['scenario_count'] >= 2, 'tone'] = 'warning'
    depth_df.loc[depth_df['scenario_count'] >= 3, 'tone'] = 'high'

    depth_df = depth_df.sort_values('scenario_count')
    depth_df = depth_df.reset_index(drop=True)

    return depth_df


def build_story_highlights(alert_cases: pd.DataFrame) -> list[dict[str, str]]:
    """Construye hallazgos cortos para abrir la historia del dashboard.

    Args:
        alert_cases: Tabla reducida de casos sospechosos.

    Returns:
        Lista de tarjetas con insight resumido.
    """
    if alert_cases.empty:
        return [
            {
                'icon': '🔎',
                'title': 'Sin señales relevantes',
                'value': 'No hay casos sospechosos',
                'hint': 'El detector no encontró ventanas con escenarios activos en este corte.',
            }
        ]

    daily_df = alert_cases.groupby(
        'transaction_day',
        as_index=False,
    )
    daily_df = daily_df.agg(
        n_cases=('transaction_day', 'size'),
        total_amount_24h=('amount_24h', 'sum'),
    )
    daily_df = daily_df.sort_values(
        ['n_cases', 'total_amount_24h'],
        ascending=[False, False],
    )
    peak_day_row = daily_df.iloc[0]

    merchant_df = build_top_alert_merchants(alert_cases)
    top_merchant_row = merchant_df.iloc[0]

    scenario_df = build_scenario_importance(alert_cases)
    top_scenario_row = scenario_df.iloc[0]

    highlight_cards = [
        {
            'icon': '📈',
            'title': 'Pico operativo',
            'value': _format_date(peak_day_row['transaction_day']),
            'hint': (
                f"{_format_int(peak_day_row['n_cases'])} casos sospechosos "
                f"y {_format_currency(peak_day_row['total_amount_24h'])} agregados."
            ),
        },
        {
            'icon': '🏪',
            'title': 'Mayor concentración',
            'value': str(top_merchant_row['top_merchant_id']),
            'hint': (
                f"{_format_int(top_merchant_row['n_cases'])} casos y "
                f"{_format_pct(top_merchant_row['pct_cases'])} del universo sospechoso."
            ),
        },
        {
            'icon': '🧠',
            'title': 'Patrón dominante',
            'value': str(top_scenario_row['scenario_label']),
            'hint': (
                f"Presente en {_format_pct(top_scenario_row['pct_cases'])} "
                f"de los casos con escenario activo."
            ),
        },
    ]

    return highlight_cards


def build_hero_metrics(
    clean_overview_df: pd.DataFrame,
    alert_table: pd.DataFrame,
    alert_cases_df: pd.DataFrame,
) -> list[dict[str, str]]:
    """Construye las tarjetas KPI principales del reporte.

    Args:
        clean_overview_df: Resumen general de la base limpia.
        alert_table: Tabla final de alertas.
        alert_cases_df: Tabla reducida de casos sospechosos.

    Returns:
        Lista de tarjetas listas para el HTML.
    """
    clean_overview_row = clean_overview_df.iloc[0]

    suspicious_cases = len(alert_cases_df)
    actionable_cases = int(alert_table['is_alert'].sum())
    high_alert_cases = int(alert_table['alert_level'].eq('alta').sum())
    suspicious_amount = float(alert_cases_df['amount_24h'].sum())

    hero_metrics = [
        {
            'label': 'Transacciones limpias',
            'value': _format_int(clean_overview_row['n_transactions']),
            'hint': 'Base depurada que alimenta el detector.',
            'icon': '🗂️',
            'context': 'Cobertura operativa',
            'tone': 'neutral',
        },
        {
            'label': 'Casos sospechosos',
            'value': _format_int(suspicious_cases),
            'hint': 'Ventanas con al menos un escenario activo.',
            'icon': '⚠️',
            'context': 'Señal detectada',
            'tone': 'warning',
        },
        {
            'label': 'Casos accionables',
            'value': _format_int(actionable_cases),
            'hint': 'Casos en nivel media o alta para revisión.',
            'icon': '🎯',
            'context': 'Priorización',
            'tone': 'accent',
        },
        {
            'label': 'Alertas altas',
            'value': _format_int(high_alert_cases),
            'hint': 'Casos con tres o más escenarios activados.',
            'icon': '🚨',
            'context': 'Escalamiento',
            'tone': 'high',
        },
        {
            'label': 'Monto 24h bajo señal',
            'value': _format_currency(suspicious_amount),
            'hint': 'Monto agregado observado en ventanas sospechosas.',
            'icon': '💰',
            'context': 'Impacto potencial',
            'tone': 'accent',
        },
    ]

    return hero_metrics


def build_alert_hero_metrics(
    alert_table: pd.DataFrame,
    alert_cases_df: pd.DataFrame,
) -> list[dict[str, str]]:
    """Construye KPIs resumidos solo a partir de la tabla final.

    Args:
        alert_table: Tabla final exportada por el modelo.
        alert_cases_df: Tabla de casos sospechosos derivada del resultado.

    Returns:
        Lista de tarjetas ejecutivas para el HTML.
    """
    actionable_cases = int(alert_table['is_alert'].sum())
    high_alert_cases = int(alert_table['alert_level'].eq('alta').sum())
    suspicious_amount = float(alert_cases_df['amount_24h'].sum())

    if 'user_id' in alert_cases_df.columns:
        n_entities = alert_cases_df['user_id'].nunique()
        entity_label = 'Usuarios con caso'
        entity_hint = 'Usuarios distintos dentro del universo sospechoso.'
    else:
        n_entities = len(alert_cases_df)
        entity_label = 'Casos visibles'
        entity_hint = 'Filas sospechosas disponibles en la salida final.'

    hero_metrics = [
        {
            'label': 'Ventanas evaluadas',
            'value': _format_int(len(alert_table)),
            'hint': 'Filas consolidadas por entidad y día en la salida del detector.',
            'icon': '🧾',
            'context': 'Cobertura operativa',
            'tone': 'neutral',
        },
        {
            'label': 'Casos sospechosos',
            'value': _format_int(len(alert_cases_df)),
            'hint': 'Ventanas con al menos un escenario activo.',
            'icon': '⚠️',
            'context': 'Señal detectada',
            'tone': 'warning',
        },
        {
            'label': 'Casos accionables',
            'value': _format_int(actionable_cases),
            'hint': 'Casos en nivel media o alta para revisión manual.',
            'icon': '🎯',
            'context': 'Priorización',
            'tone': 'accent',
        },
        {
            'label': 'Alertas altas',
            'value': _format_int(high_alert_cases),
            'hint': 'Casos con tres o más escenarios activados.',
            'icon': '🚨',
            'context': 'Escalamiento',
            'tone': 'high',
        },
        {
            'label': 'Monto 24h bajo señal',
            'value': _format_currency(suspicious_amount),
            'hint': 'Monto agregado observado en ventanas sospechosas.',
            'icon': '💰',
            'context': 'Impacto potencial',
            'tone': 'accent',
        },
        {
            'label': entity_label,
            'value': _format_int(n_entities),
            'hint': entity_hint,
            'icon': '👤',
            'context': 'Cobertura de entidades',
            'tone': 'neutral',
        },
    ]

    return hero_metrics


def build_report_payload_from_alert_table(
    dataset_name: str,
    generated_at: str,
    alert_table: pd.DataFrame,
    entity_cols: list[str] | None = None,
    segment_cols: list[str] | None = None,
) -> dict[str, Any]:
    """Construye el payload del HTML solo desde la tabla final exportada.

    Args:
        dataset_name: Nombre de la tabla resultado usada como fuente.
        generated_at: Marca de tiempo de generacion del reporte.
        alert_table: Tabla final exportada por el modelo.
        entity_cols: Unidad analitica usada por el detector.
        segment_cols: Segmentacion usada por el detector.

    Returns:
        Diccionario con metadata, tablas y casos para renderizar el HTML.
    """
    if entity_cols is None:
        entity_cols = detection.DEFAULT_ENTITY_COLS

    if segment_cols is None:
        segment_cols = ['transaction_type']

    alert_cases_df = build_alert_cases_table(alert_table)
    hero_metrics = build_alert_hero_metrics(
        alert_table=alert_table,
        alert_cases_df=alert_cases_df,
    )
    top_alert_merchants_df = build_top_alert_merchants(alert_cases_df)
    priority_funnel_df = build_priority_funnel(
        alert_table=alert_table,
        alert_cases=alert_cases_df,
    )
    scenario_importance_df = build_scenario_importance(alert_cases_df)
    scenario_depth_df = build_scenario_depth_summary(alert_cases_df)
    story_highlights = build_story_highlights(alert_cases_df)

    date_range = (
        f"{_format_date(alert_table['transaction_day'].min())}"
        f" a {_format_date(alert_table['transaction_day'].max())}"
    )

    tables = {
        'alert_level_monitoring': detection.build_alert_level_monitoring_table(
            alert_table=alert_table,
        ),
        'top_alert_merchants': top_alert_merchants_df,
        'alert_type_summary': build_alert_type_summary(alert_cases_df),
        'priority_funnel': priority_funnel_df,
        'scenario_importance': scenario_importance_df,
        'scenario_depth': scenario_depth_df,
    }

    payload = {
        'metadata': {
            'dataset_name': dataset_name,
            'generated_at': generated_at,
            'entity_definition': ' + '.join(entity_cols),
            'segment_definition': ' + '.join(segment_cols),
            'date_range': date_range,
        },
        'hero_metrics': hero_metrics,
        'tables': tables,
        'alert_cases': alert_cases_df,
        'story_highlights': story_highlights,
    }

    return payload


def build_report_payload_from_artifacts(
    dataset_name: str,
    generated_at: str,
    entity_cols: list[str],
    segment_cols: list[str],
    hero_metrics: list[dict[str, str]],
    summary_tables: dict[str, pd.DataFrame],
    alert_table: pd.DataFrame,
) -> dict[str, Any]:
    """Empaqueta artefactos ya calculados para el render del HTML.

    Args:
        dataset_name: Nombre del archivo fuente analizado.
        generated_at: Marca de tiempo del pipeline.
        entity_cols: Unidad analitica usada por el detector.
        segment_cols: Segmentacion usada para umbrales.
        hero_metrics: Tarjetas KPI del reporte.
        summary_tables: Tablas resumen del pipeline.
        alert_table: Tabla final de alertas, idealmente leida desde disco.

    Returns:
        Diccionario con metadata, tablas y casos para renderizar el HTML.
    """
    alert_cases_df = build_alert_cases_table(alert_table)
    top_alert_merchants_df = build_top_alert_merchants(alert_cases_df)
    alert_type_summary_df = build_alert_type_summary(alert_cases_df)
    priority_funnel_df = build_priority_funnel(
        alert_table=alert_table,
        alert_cases=alert_cases_df,
    )
    scenario_importance_df = build_scenario_importance(alert_cases_df)
    scenario_depth_df = build_scenario_depth_summary(alert_cases_df)
    story_highlights = build_story_highlights(alert_cases_df)
    clean_overview_row = summary_tables['clean_overview'].iloc[0]

    date_range = (
        f"{_format_date(clean_overview_row['min_transaction_date'])}"
        f" a {_format_date(clean_overview_row['max_transaction_date'])}"
    )

    tables = dict(summary_tables)
    tables['top_alert_merchants'] = top_alert_merchants_df
    tables['alert_type_summary'] = alert_type_summary_df
    tables['priority_funnel'] = priority_funnel_df
    tables['scenario_importance'] = scenario_importance_df
    tables['scenario_depth'] = scenario_depth_df

    payload = {
        'metadata': {
            'dataset_name': dataset_name,
            'generated_at': generated_at,
            'entity_definition': ' + '.join(entity_cols),
            'segment_definition': ' + '.join(segment_cols),
            'date_range': date_range,
        },
        'hero_metrics': hero_metrics,
        'tables': tables,
        'alert_cases': alert_cases_df,
        'story_highlights': story_highlights,
    }

    return payload


def build_report_payload(
    raw_data: pd.DataFrame,
    dataset_name: str,
    entity_cols: list[str] | None = None,
    segment_cols: list[str] | None = None,
) -> dict[str, Any]:
    """Construye todas las tablas necesarias para el reporte HTML.

    Args:
        raw_data: DataFrame cargado desde un parquet local.
        dataset_name: Nombre del archivo analizado.
        entity_cols: Unidad analitica del detector.
        segment_cols: Segmentacion usada para umbrales.

    Returns:
        Diccionario con tablas, metricas y datos para el HTML.
    """
    if entity_cols is None:
        entity_cols = detection.DEFAULT_ENTITY_COLS

    if segment_cols is None:
        segment_cols = ['transaction_type']

    raw_overview_df = eda.build_data_overview(raw_data)

    deduplicated_data = cleaning.deduplicate_transaction_ids(raw_data)
    required_clean_data = cleaning.drop_null_required_fields(deduplicated_data)
    clean_data = cleaning.drop_non_positive_transaction_amounts(required_clean_data)

    clean_overview_df = eda.build_data_overview(clean_data)
    cleaning_summary_df = build_cleaning_summary(
        raw_data=raw_data,
        deduplicated_data=deduplicated_data,
        required_clean_data=required_clean_data,
        clean_data=clean_data,
    )

    type_distribution_df = eda.build_categorical_distribution(
        clean_data,
        'transaction_type',
    )

    _, user_activity_summary_df = eda.build_user_activity(clean_data)

    window_features = detection.build_window_features(
        data=clean_data,
        entity_cols=entity_cols,
        window='24h',
    )

    window_feature_distribution_df = detection.build_window_feature_distribution(
        window_features=window_features,
        value_cols=['count', 'sum', 'cv'],
    )

    alert_table = detection.build_scenario_detection_table(
        data=clean_data,
        entity_cols=entity_cols,
        segment_cols=segment_cols,
        window='24h',
    )

    alert_level_monitoring_df = detection.build_alert_level_monitoring_table(
        alert_table=alert_table,
    )

    alert_cases_df = build_alert_cases_table(alert_table)
    top_alert_merchants_df = build_top_alert_merchants(alert_cases_df)
    alert_type_summary_df = build_alert_type_summary(alert_cases_df)

    report_generated_at = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
    hero_metrics = build_hero_metrics(
        clean_overview_df=clean_overview_df,
        alert_table=alert_table,
        alert_cases_df=alert_cases_df,
    )

    summary_tables = {
        'cleaning_summary': cleaning_summary_df,
        'type_distribution': type_distribution_df,
        'user_activity_summary': user_activity_summary_df,
        'window_feature_distribution': window_feature_distribution_df,
        'alert_level_monitoring': alert_level_monitoring_df,
        'top_alert_merchants': top_alert_merchants_df,
        'alert_type_summary': alert_type_summary_df,
    }

    return build_report_payload_from_artifacts(
        dataset_name=dataset_name,
        generated_at=report_generated_at,
        entity_cols=entity_cols,
        segment_cols=segment_cols,
        hero_metrics=hero_metrics,
        summary_tables=summary_tables,
        alert_table=alert_table,
    )


def render_html_report(
    report_payload: dict[str, Any],
    title: str,
    table_row_limit: int = 250,
) -> str:
    """Renderiza el reporte HTML final.

    Args:
        report_payload: Diccionario con tablas y metricas del reporte.
        title: Titulo principal del documento.
        table_row_limit: Numero maximo de filas visibles en la tabla interactiva.

    Returns:
        HTML completo en una sola cadena.
    """
    metadata = report_payload['metadata']
    tables = report_payload['tables']
    alert_cases_df = report_payload['alert_cases']
    story_highlights = report_payload['story_highlights']

    hero_cards_html = ''.join(
        _render_metric_card(metric)
        for metric in report_payload['hero_metrics']
    )

    story_highlights_html = _render_story_cards(story_highlights)

    priority_funnel_html = _render_progress_list(
        tables['priority_funnel'],
    )

    level_story_df = tables['alert_level_monitoring'].loc[
        tables['alert_level_monitoring']['volume'] > 0,
        :,
    ]
    level_story_df = level_story_df.reset_index(drop=True)
    level_story_df['icon'] = level_story_df['alert_level'].astype(str)
    level_story_df['tone'] = 'neutral'
    level_story_df.loc[level_story_df['alert_level'] == 'alta', 'icon'] = '🚨'
    level_story_df.loc[level_story_df['alert_level'] == 'media', 'icon'] = '🎯'
    level_story_df.loc[level_story_df['alert_level'] == 'pre_alerta', 'icon'] = '👀'
    level_story_df.loc[level_story_df['alert_level'] == 'sin_alerta', 'icon'] = '✅'
    level_story_df.loc[level_story_df['alert_level'] == 'alta', 'tone'] = 'high'
    level_story_df.loc[level_story_df['alert_level'] == 'media', 'tone'] = 'warning'
    level_story_df.loc[level_story_df['alert_level'] == 'sin_alerta', 'tone'] = 'success'

    level_monitoring_html = _render_rank_bars(
        data=level_story_df,
        label_col='alert_level',
        value_col='volume',
        width_col='pct_total',
        icon_col='icon',
        tone_col='tone',
        value_formatter=_format_int,
        note_builder=lambda row: (
            f"{_format_pct(row['pct_total'])} del total | "
            f"promedio diario {_format_decimal(row['avg_daily_volume'])} | "
            f"P95 {_format_decimal(row['p95_daily_volume'])}"
        ),
    )

    scenario_depth_html = _render_rank_bars(
        data=tables['scenario_depth'],
        label_col='scenario_bucket',
        value_col='n_cases',
        width_col='pct_cases',
        icon_col='icon',
        tone_col='tone',
        value_formatter=_format_int,
        note_builder=lambda row: (
            f"{_format_pct(row['pct_cases'])} de los casos sospechosos | "
            f"monto medio {_format_currency(row['avg_amount_24h'])}"
        ),
    )

    scenario_importance_html = _render_rank_bars(
        data=tables['scenario_importance'],
        label_col='scenario_label',
        value_col='n_cases',
        width_col='pct_cases',
        icon_col='icon',
        tone_col='tone',
        value_formatter=_format_int,
        note_builder=lambda row: (
            f"{_format_pct(row['pct_cases'])} de los casos sospechosos | "
            f"monto medio {_format_currency(row['avg_amount_24h'])}"
        ),
    )

    alert_type_summary_html = _render_rank_bars(
        data=tables['alert_type_summary'],
        label_col='transaction_type',
        value_col='n_cases',
        width_col='pct_cases',
        icon_col=None,
        tone_col=None,
        value_formatter=_format_int,
        note_builder=lambda row: (
            f"{_format_pct(row['pct_cases'])} de los casos | "
            f"{_format_int(row['high_alert_cases'])} alertas altas | "
            f"monto {_format_currency(row['total_amount_24h'])}"
        ),
    )

    top_alert_merchants_html = _render_rank_bars(
        data=tables['top_alert_merchants'],
        label_col='top_merchant_id',
        value_col='n_cases',
        width_col='pct_cases',
        value_formatter=_format_int,
        note_builder=lambda row: (
            f"{_format_pct(row['pct_cases'])} de los casos | "
            f"{_format_int(row['high_alert_cases'])} alertas altas | "
            f"monto {_format_currency(row['total_amount_24h'])}"
        ),
    )

    client_payload = {
        'meta': {
            'table_row_limit': table_row_limit,
        },
        'filter_options': {
            'alert_levels': _sorted_unique_values(alert_cases_df, 'alert_level'),
            'transaction_types': _sorted_unique_values(alert_cases_df, 'transaction_type'),
        },
        'alert_cases': _dataframe_to_records(alert_cases_df),
    }

    client_payload_json = json.dumps(
        client_payload,
        ensure_ascii=False,
    )

    client_payload_json = client_payload_json.replace('</', '<\\/')

    return _build_html_document(
        title=title,
        metadata=metadata,
        hero_cards_html=hero_cards_html,
        story_highlights_html=story_highlights_html,
        priority_funnel_html=priority_funnel_html,
        level_monitoring_html=level_monitoring_html,
        scenario_depth_html=scenario_depth_html,
        scenario_importance_html=scenario_importance_html,
        alert_type_summary_html=alert_type_summary_html,
        top_alert_merchants_html=top_alert_merchants_html,
        client_payload_json=client_payload_json,
    )


def write_html_report(html_content: str, output_path: str | Path) -> None:
    """Escribe el HTML final en disco.

    Args:
        html_content: Documento HTML completo.
        output_path: Ruta destino del archivo.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding='utf-8-sig')


def _build_html_document(
    title: str,
    metadata: dict[str, Any],
    hero_cards_html: str,
    story_highlights_html: str,
    priority_funnel_html: str,
    level_monitoring_html: str,
    scenario_depth_html: str,
    scenario_importance_html: str,
    alert_type_summary_html: str,
    top_alert_merchants_html: str,
    client_payload_json: str,
) -> str:
    """Arma el documento HTML completo a partir de fragmentos."""
    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="es">',
        '<head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<title>{html.escape(title)}</title>',
        REPORT_STYLES,
        '</head>',
        '<body>',
        '<div class="page-shell">',
        '<section class="hero">',
        '<article class="hero-card">',
        '<div class="hero-brand">',
        '<img class="hero-logo" src="assets/nequi_logo.png" alt="Logo de Nequi">',
        '</div>',
        '<p class="eyebrow">Detector heurístico de fraccionamiento</p>',
        f'<h1>{html.escape(title)}</h1>',
        (
            '<p class="hero-lead">'
            'HTML ejecutivo para contar la historia del detector: primero el impacto, '
            'luego el comportamiento del modelo heurístico y, al final, el diagnóstico '
            'que permite bajar hasta el caso puntual.'
            '</p>'
        ),
        '<div class="meta-row">',
        f'<span class="meta-pill">Archivo: {html.escape(metadata["dataset_name"])}</span>',
        f'<span class="meta-pill">Período: {html.escape(metadata["date_range"])}</span>',
        f'<span class="meta-pill">Generado: {html.escape(metadata["generated_at"])}</span>',
        f'<span class="meta-pill">Entidad: {html.escape(metadata["entity_definition"])}</span>',
        '</div>',
        '</article>',
        '<aside class="hero-card">',
        '<p class="eyebrow">Cómo leer este HTML</p>',
        '<h2>Secuencia de consumo</h2>',
        '<ul class="bullet-list">',
        '<li>Nivel 1: KPIs de cobertura, backlog y monto potencialmente fraccionado.</li>',
        '<li>Nivel 2: severidad y comportamiento operativo del detector, traducidos a negocio.</li>',
        '<li>Nivel 3: escenarios que explican la alerta y drilldown interactivo por segmento.</li>',
        '<li>Nota metodológica: no hay etiquetas confirmadas, por eso el rendimiento se presenta como desempeño operativo del detector y no como precisión supervisada.</li>',
        '</ul>',
        '</aside>',
        '</section>',
        '<section class="section">',
        '<div class="section-head">',
        '<div>',
        '<p class="section-kicker">Nivel 1 | Visión ejecutiva</p>',
        '<h2>📌 Qué está pasando y por qué importa</h2>',
        '<p>Abre con el volumen priorizado por el detector y tres hallazgos que ayudan a explicar el corte sin entrar aún al detalle técnico.</p>',
        '</div>',
        '</div>',
        f'<div class="metric-grid">{hero_cards_html}</div>',
        '<div class="grid-two">',
        _render_panel(
            title='📖 Lectura ejecutiva',
            description='Hallazgos cortos para abrir la conversación y orientar la revisión manual.',
            inner_html=story_highlights_html,
        ),
        _render_panel(
            title='🎯 Embudo operativo del detector',
            description='Bullet chart liviano para ver cuántas ventanas pasan de observación a backlog accionable.',
            inner_html=priority_funnel_html,
        ),
        '</div>',
        '</section>',
        '<section class="section">',
        '<div class="section-head">',
        '<div>',
        '<p class="section-kicker">Nivel 2 | Rendimiento del detector</p>',
        '<h2>⚙️ Cómo se comporta la señal en la operación</h2>',
        '<p>Estas vistas traducen el rendimiento del detector a volumen, severidad y presión operativa por segmento.</p>',
        '</div>',
        '</div>',
        '<div class="grid-two">',
        _render_panel(
            title='⚠️ Severidad por nivel',
            description='Ranking horizontal por nivel de alerta. Muestra volumen, participación y estabilidad diaria.',
            inner_html=level_monitoring_html,
        ),
        _render_panel(
            title='📶 Profundidad de la señal',
            description='Cuántos escenarios se activan por caso. A mayor profundidad, mayor intensidad de la alerta.',
            inner_html=scenario_depth_html,
        ),
        '</div>',
        '<div class="panel" style="margin-top: 16px;">',
        '<h3>💳 Segmentos por tipo de transacción</h3>',
        '<p>Barras horizontales por tipo de transacción para ver dónde se acumula el volumen sospechoso y la presión de alertas altas.</p>',
        f'{alert_type_summary_html}',
        '</div>',
        '</section>',
        '<section class="section">',
        '<div class="section-head">',
        '<div>',
        '<p class="section-kicker">Nivel 3 | Explicabilidad y diagnóstico</p>',
        '<h2>🧠 Qué explica la alerta y dónde concentrarla</h2>',
        '<p>La explicabilidad se muestra por escenarios activados y por focos de concentración observables en el resultado final.</p>',
        '</div>',
        '</div>',
        '<div class="grid-two">',
        _render_panel(
            title='🧠 Importancia de escenarios',
            description='Barras horizontales limpias para ver qué hipótesis explican más casos y con qué monto medio aparecen.',
            inner_html=scenario_importance_html,
        ),
        _render_panel(
            title='🏪 Merchants más concentrados',
            description='Ranking de merchants dominantes dentro del universo sospechoso para priorizar revisión por contraparte observable.',
            inner_html=top_alert_merchants_html,
        ),
        '</div>',
        '</section>',
        '<section class="section">',
        '<div class="section-head">',
        '<div>',
        '<p class="section-kicker">Drilldown interactivo</p>',
        '<h2>🔎 Explorar los casos de lo general a lo particular</h2>',
        (
            '<p>Aplica filtros y revisa cómo cambian los KPIs, la serie diaria, la concentración por merchant '
            'y el detalle de casos. Este bloque reemplaza el dashboard sin depender de una app web.</p>'
        ),
        '</div>',
        '</div>',
        '<div class="panel">',
        '<div class="filters">',
        '<div class="filter-field">',
        '<label for="alert-level-filter">Nivel de alerta</label>',
        '<select id="alert-level-filter"><option value="all">Todos</option></select>',
        '</div>',
        '<div class="filter-field">',
        '<label for="transaction-type-filter">Tipo de transacción</label>',
        '<select id="transaction-type-filter"><option value="all">Todos</option></select>',
        '</div>',
        '<div class="filter-field">',
        '<label for="start-date-filter">Desde</label>',
        '<input id="start-date-filter" type="date">',
        '</div>',
        '<div class="filter-field">',
        '<label for="end-date-filter">Hasta</label>',
        '<input id="end-date-filter" type="date">',
        '</div>',
        '<div class="filter-field">',
        '<label for="search-filter">Búsqueda libre</label>',
        '<input id="search-filter" type="search" placeholder="user_id, account, merchant, motivo...">',
        '</div>',
        '<div class="filter-field">',
        '<label for="reset-filters">Acción</label>',
        '<button id="reset-filters" type="button">Limpiar filtros</button>',
        '</div>',
        '</div>',
        '<div id="filtered-metrics" class="metric-grid"></div>',
        '</div>',
        '<div class="panel" style="margin-top: 16px;">',
        '<h3>📈 Serie diaria filtrada</h3>',
        '<p>Gráfico de barras con tiempo en el eje X. Sirve para detectar picos de actividad del subconjunto visible.</p>',
        '<div id="filtered-bar-chart" class="bar-chart"></div>',
        '</div>',
        '<div class="panel" style="margin-top: 16px;">',
        '<h3>🏪 Top merchants filtrados</h3>',
        '<p>Concentración de casos visibles sobre los merchants dominantes del subconjunto actual.</p>',
        '<div id="filtered-merchant-table"></div>',
        '</div>',
        '<div class="panel" style="margin-top: 16px;">',
        '<h3>🧾 Tabla filtrable de casos</h3>',
        '<p>Último nivel de detalle para analistas: conserva el motivo explicable, la entidad y el contexto observable de cada ventana.</p>',
        '<div id="filtered-table-summary" class="summary-line"></div>',
        '<div class="table-wrap">',
        '<table>',
        '<thead>',
        '<tr>',
        '<th>Día</th>',
        '<th>Nivel</th>',
        '<th>Tipo</th>',
        '<th>User</th>',
        '<th>Cuenta</th>',
        '<th>Merchant</th>',
        '<th>Subsidiary</th>',
        '<th>Tx 24h</th>',
        '<th>Monto 24h</th>',
        '<th>Motivo</th>',
        '</tr>',
        '</thead>',
        '<tbody id="filtered-cases-body"></tbody>',
        '</table>',
        '</div>',
        (
            '<p class="note">La tabla mantiene un subconjunto visible para que el HTML siga ligero; '
            'los KPIs y filtros se calculan sobre todos los casos sospechosos cargados en el documento.</p>'
        ),
        '</div>',
        f'<script id="report-data" type="application/json">{client_payload_json}</script>',
        REPORT_SCRIPT,
        '</section>',
        '</div>',
        '</body>',
        '</html>',
    ]

    return '\n'.join(html_parts)


def _build_alert_reason(row: pd.Series) -> str:
    """Resume en texto los escenarios activados para una fila."""
    active_labels = []

    for col, label in SCENARIO_LABELS.items():
        if row.get(col, 0) == 1:
            active_labels.append(label)

    if len(active_labels) == 0:
        return 'sin escenario activo'

    return '; '.join(active_labels)


def _render_metric_card(metric: dict[str, str]) -> str:
    """Renderiza una tarjeta KPI."""
    label = html.escape(metric['label'])
    value = html.escape(metric['value'])
    hint = html.escape(metric['hint'])
    icon = html.escape(metric.get('icon', '•'))
    context = html.escape(metric.get('context', 'Indicador'))
    tone = html.escape(metric.get('tone', 'neutral'))

    return (
        f'<article class="hero-card metric-card tone-{tone}">'
        '<div class="metric-card-head">'
        f'<span class="metric-icon">{icon}</span>'
        f'<span class="metric-context">{context}</span>'
        '</div>'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-hint">{hint}</div>'
        '</article>'
    )


def _render_story_cards(stories: list[dict[str, str]]) -> str:
    """Renderiza tarjetas cortas de hallazgos."""
    if len(stories) == 0:
        return '<div class="empty-state">No hay hallazgos disponibles para esta vista.</div>'

    parts = ['<div class="story-grid">']

    for story in stories:
        icon = html.escape(story.get('icon', '•'))
        title = html.escape(story.get('title', 'Hallazgo'))
        value = html.escape(story.get('value', 'NA'))
        hint = html.escape(story.get('hint', ''))

        parts.extend(
            [
                '<article class="story-card">',
                f'<div class="story-icon">{icon}</div>',
                '<div>',
                f'<p class="story-title">{title}</p>',
                f'<div class="story-value">{value}</div>',
                f'<p class="story-hint">{hint}</p>',
                '</div>',
                '</article>',
            ]
        )

    parts.append('</div>')

    return ''.join(parts)


def _render_progress_list(items: pd.DataFrame) -> str:
    """Renderiza un embudo simple con barras de progreso."""
    if items.empty:
        return '<div class="empty-state">No hay etapas disponibles para este embudo.</div>'

    parts = ['<div class="progress-list">']

    for _, row in items.iterrows():
        icon = html.escape(str(row.get('icon', '•')))
        label = html.escape(str(row['label']))
        value = html.escape(_format_int(row['value']))
        tone = html.escape(str(row.get('tone', 'neutral')))
        width = max(6, round(float(row['pct_total'])))
        note = html.escape(
            f"{_format_pct(row['pct_total'])} del universo evaluado. {row['hint']}"
        )

        parts.extend(
            [
                '<article class="progress-item">',
                '<div class="progress-head">',
                f'<div class="progress-label"><span class="metric-icon">{icon}</span><span>{label}</span></div>',
                f'<div class="progress-value">{value}</div>',
                '</div>',
                '<div class="progress-track">',
                f'<div class="progress-fill tone-{tone}" style="width: {width}%;"></div>',
                '</div>',
                f'<div class="progress-note">{note}</div>',
                '</article>',
            ]
        )

    parts.append('</div>')

    return ''.join(parts)


def _render_rank_bars(
    data: pd.DataFrame,
    label_col: str,
    value_col: str,
    note_builder: Callable[[pd.Series], str],
    width_col: str | None = None,
    icon_col: str | None = None,
    tone_col: str | None = None,
    value_formatter: Callable[[Any], str] | None = None,
) -> str:
    """Renderiza un ranking compacto con barras horizontales."""
    if data.empty:
        return '<div class="empty-state">No hay datos disponibles para esta vista.</div>'

    if value_formatter is None:
        value_formatter = _format_default

    width_source = value_col

    if width_col is not None:
        width_source = width_col

    max_width = float(data.loc[:, width_source].max())

    if max_width <= 0:
        max_width = 1.0

    parts = ['<div class="rank-list">']

    for _, row in data.iterrows():
        label = html.escape(str(row[label_col]))
        value = html.escape(value_formatter(row[value_col]))
        note = html.escape(note_builder(row))
        icon = ''
        tone = 'neutral'

        if icon_col is not None:
            icon = html.escape(str(row.get(icon_col, '')))

        if tone_col is not None:
            tone = html.escape(str(row.get(tone_col, 'neutral')))

        width = max(8, round(100 * float(row[width_source]) / max_width))
        icon_html = ''

        if icon:
            icon_html = f'<span class="metric-icon">{icon}</span>'

        parts.extend(
            [
                '<article class="rank-item">',
                '<div class="rank-head">',
                f'<div class="rank-label-wrap">{icon_html}<span class="rank-label">{label}</span></div>',
                f'<div class="rank-value">{value}</div>',
                '</div>',
                '<div class="rank-track">',
                f'<div class="rank-fill tone-{tone}" style="width: {width}%;"></div>',
                '</div>',
                f'<div class="rank-note">{note}</div>',
                '</article>',
            ]
        )

    parts.append('</div>')

    return ''.join(parts)


def _render_panel(
    title: str,
    description: str,
    inner_html: str,
) -> str:
    """Envuelve contenido en una tarjeta reutilizable."""
    return (
        '<article class="panel">'
        f'<h3>{html.escape(title)}</h3>'
        f'<p>{html.escape(description)}</p>'
        f'{inner_html}'
        '</article>'
    )


def _render_table(
    data: pd.DataFrame,
    columns: list[tuple[str, str]],
    formatters: dict[str, Callable[[Any], str]] | None = None,
) -> str:
    """Renderiza una tabla HTML simple a partir de un DataFrame."""
    formatters = formatters or {}

    if data.empty:
        return '<div class="empty-state">No hay datos disponibles para esta vista.</div>'

    header_html = ''.join(
        f'<th>{html.escape(label)}</th>'
        for _, label in columns
    )

    row_html_list = []

    for _, row in data.iterrows():
        cells = []

        for col, _ in columns:
            value = row[col]
            formatter = formatters.get(col)

            if formatter is not None:
                rendered_value = formatter(value)
            else:
                rendered_value = _format_default(value)

            cells.append(f'<td>{html.escape(rendered_value)}</td>')

        row_html_list.append(f"<tr>{''.join(cells)}</tr>")

    body_html = ''.join(row_html_list)

    return (
        '<div class="table-wrap">'
        '<table>'
        f'<thead><tr>{header_html}</tr></thead>'
        f'<tbody>{body_html}</tbody>'
        '</table>'
        '</div>'
    )


def _sorted_unique_values(data: pd.DataFrame, col: str) -> list[str]:
    """Devuelve valores unicos ordenados para poblar filtros."""
    if data.empty:
        return []

    values = data.loc[:, col].dropna().astype(str).unique().tolist()
    values = sorted(values)

    return values


def _dataframe_to_records(data: pd.DataFrame) -> list[dict[str, Any]]:
    """Convierte un DataFrame en registros serializables a JSON."""
    records = []

    for row in data.to_dict(orient='records'):
        record = {}

        for col, value in row.items():
            record[col] = _serialize_value(value)

        records.append(record)

    return records


def _serialize_value(value: Any) -> Any:
    """Normaliza tipos de pandas y numpy a objetos serializables."""
    if hasattr(value, 'item'):
        value = value.item()

    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if hasattr(value, 'isoformat') and not isinstance(value, str):
        return value.isoformat()

    return value


def _safe_pct(numerator: int | float, denominator: int | float) -> float:
    """Calcula un porcentaje sobre base 100 evitando divisiones por cero."""
    if denominator == 0:
        return 0.0

    return 100 * numerator / denominator


def _format_default(value: Any) -> str:
    """Formatea valores genericos para tablas estaticas."""
    if pd.isna(value):
        return 'NA'

    if isinstance(value, (int, float)):
        if float(value).is_integer():
            return _format_int(value)

        return _format_decimal(value)

    return str(value)


def _format_int(value: Any) -> str:
    """Formatea enteros con separador local sencillo."""
    number = int(round(float(value)))
    text = f'{number:,}'
    text = text.replace(',', '.')

    return text


def _format_decimal(value: Any) -> str:
    """Formatea decimales con dos cifras."""
    number = float(value)
    text = f'{number:,.2f}'
    text = text.replace(',', '_')
    text = text.replace('.', ',')
    text = text.replace('_', '.')

    return text


def _format_currency(value: Any) -> str:
    """Formatea montos como moneda sin decimales."""
    return f'$ {_format_int(value)}'


def _format_pct(value: Any) -> str:
    """Formatea porcentajes ya expresados sobre 100."""
    return f'{_format_decimal(value)}%'


def _format_ratio_pct(value: Any) -> str:
    """Formatea razones entre 0 y 1 como porcentaje."""
    return _format_pct(100 * float(value))


def _format_date(value: Any) -> str:
    """Formatea fechas en ISO corto."""
    if pd.isna(value):
        return 'NA'

    return pd.Timestamp(value).strftime('%Y-%m-%d')
