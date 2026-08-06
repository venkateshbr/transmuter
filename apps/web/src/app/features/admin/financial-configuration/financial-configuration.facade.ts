import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import {
  FinancialBridgeRow,
  FinancialCostCategory,
  FinancialEngineConfiguration,
  FinancialMetricDefinition,
  FinancialReportingSettings,
  FinancialScenario,
  FinancialAttributeDefinition,
} from './financial-configuration.models';

@Injectable()
export class FinancialConfigurationFacade {
  private readonly api = inject(ApiService);

  load(): Observable<FinancialEngineConfiguration> {
    return this.api.get<FinancialEngineConfiguration>('/financial-engine-configuration');
  }

  loadAnnualBaselines(): Observable<{
    values: Array<{ metric_definition_id: string; baseline_year: number; value: string }>;
  }> {
    return this.api.get('/admin/financial-engine/annual-baselines');
  }

  saveSettings(settings: FinancialReportingSettings): Observable<FinancialReportingSettings> {
    return this.api.put('/admin/financial-engine/reporting-settings', settings);
  }

  saveMetric(metric: FinancialMetricDefinition): Observable<FinancialMetricDefinition> {
    const payload = {
      key: metric.key,
      label: metric.label,
      description: metric.description || null,
      group_key: metric.group_key || null,
      value_type: metric.value_type,
      unit: metric.unit || null,
      direction: metric.direction || 'increase_good',
      aggregation: metric.aggregation,
      rollup_type: metric.rollup_type || null,
      is_benefit: metric.is_benefit,
      benefit_class: metric.benefit_class || null,
      cost_behavior: metric.cost_behavior || null,
      formula: metric.aggregation === 'formula' ? metric.formula || null : null,
      formula_inputs: metric.aggregation === 'formula' ? metric.formula_inputs : [],
      precision: Number(metric.precision ?? 4),
      display_order: Number(metric.display_order || 0),
      applies_to: metric.applies_to || 'opt_in',
      validation: metric.validation || {},
      is_system: Boolean(metric.is_system),
      is_active: metric.is_active !== false,
    };
    return metric.id
      ? this.api.patch(`/admin/financial-engine/metrics/${metric.id}`, payload)
      : this.api.post('/admin/financial-engine/metrics', payload);
  }

  saveScenario(row: FinancialScenario): Observable<FinancialScenario> {
    const payload = {
      key: row.key,
      label: row.label,
      kind: row.kind,
      is_primary: Boolean(row.is_primary),
      is_system: Boolean(row.is_system),
      is_active: row.is_active !== false,
      display_order: Number(row.display_order || 0),
    };
    return row.id
      ? this.api.patch(`/admin/financial-engine/scenarios/${row.id}`, payload)
      : this.api.post('/admin/financial-engine/scenarios', payload);
  }

  saveBridgeRow(row: FinancialBridgeRow): Observable<FinancialBridgeRow> {
    const isNet = row.row_kind === 'net';
    const payload = {
      id: row.id || null,
      key: row.key,
      label: row.label,
      row_kind: row.row_kind,
      metric_definition_ids: isNet ? [] : row.metric_definition_ids,
      cost_category_ids: isNet ? [] : row.cost_category_ids,
      cost_category_keys: isNet ? [] : row.cost_category_keys || [],
      sign: Number(row.sign) < 0 ? -1 : 1,
      display_order: Number(row.display_order || 0),
      is_active: row.is_active !== false,
    };
    return row.id
      ? this.api.patch(`/admin/financial-engine/bridge-rows/${row.id}`, payload)
      : this.api.post('/admin/financial-engine/bridge-rows', payload);
  }

  saveCostCategory(row: FinancialCostCategory): Observable<FinancialCostCategory> {
    const payload = {
      id: row.id || null,
      key: row.key,
      label: row.label,
      group_key: row.group_key || null,
      rollup_type: row.rollup_type || null,
      display_order: Number(row.display_order || 0),
      attributes: row.attributes || {},
      is_system: Boolean(row.is_system),
      is_active: row.is_active !== false,
    };
    return row.id
      ? this.api.patch(`/admin/financial-engine/cost-categories/${row.id}`, payload)
      : this.api.post('/admin/financial-engine/cost-categories', payload);
  }

  saveAttribute(row: FinancialAttributeDefinition): Observable<FinancialAttributeDefinition> {
    const payload = {
      id: row.id || null,
      key: row.key,
      label: row.label,
      entity_type: row.entity_type,
      value_type: row.value_type,
      options: row.options || [],
      is_required: Boolean(row.is_required),
      display_order: Number(row.display_order || 0),
      is_active: row.is_active !== false,
    };
    return row.id
      ? this.api.patch(`/admin/financial-engine/attribute-definitions/${row.id}`, payload)
      : this.api.post('/admin/financial-engine/attribute-definitions', payload);
  }

  saveAnnualBaselines(
    values: Array<{ metric_definition_id: string; baseline_year: number; value: string }>,
  ): Observable<unknown> {
    return this.api.put('/admin/financial-engine/annual-baselines', { values });
  }
}
