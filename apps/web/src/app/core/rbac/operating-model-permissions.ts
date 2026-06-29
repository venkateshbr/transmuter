export type OperatingModelPermission =
  | 'portfolio.view'
  | 'initiatives.view_all'
  | 'initiatives.manage_all'
  | 'initiatives.manage_assigned'
  | 'initiatives.manage_workstream'
  | 'users.manage'
  | 'tenant_setup.manage'
  | 'financials.manage'
  | 'financials.manage_assigned'
  | 'benefits.validate'
  | 'benefits.realize'
  | 'shared_costs.manage'
  | 'governance.manage'
  | 'program_cadence.manage'
  | 'execution_evidence.manage'
  | 'execution_evidence.manage_assigned'
  | 'execution_evidence.manage_workstream';

export interface OperatingModelRoleOption {
  id: string;
  name: string;
  description: string;
}

export const OPERATING_MODEL_ROLES: OperatingModelRoleOption[] = [
  {
    id: 'transformation_office',
    name: 'Transformation Office',
    description: 'Full tenant and portfolio management.',
  },
  {
    id: 'tenant_admin',
    name: 'Tenant Administrator',
    description: 'Users, access, tenant setup, dimensions, and dashboard configuration.',
  },
  {
    id: 'pmo_lead',
    name: 'PMO Lead / Governance Manager',
    description: 'Governance, meetings, actions, risks, KPIs, milestones, and cadence.',
  },
  {
    id: 'finance_lead',
    name: 'Finance Lead / Benefits Controller',
    description: 'Financial configuration, validation, shared costs, and benefit realization.',
  },
  {
    id: 'workstream_lead',
    name: 'Workstream Lead',
    description: 'Assigned workstream portfolio visibility and execution updates.',
  },
  {
    id: 'initiative_owner',
    name: 'Initiative Owner',
    description: 'Assigned initiative delivery, evidence, status, and financial assumptions.',
  },
  {
    id: 'business_benefit_owner',
    name: 'Business Benefit Owner',
    description: 'Benefit realization evidence and sustainment confirmation.',
  },
  {
    id: 'executive_sponsor',
    name: 'Executive Sponsor',
    description: 'Read-only executive portfolio and control-tower access.',
  },
  {
    id: 'viewer',
    name: 'Management Viewer',
    description: 'Read-only portfolio, dashboard, and report access.',
  },
];

const ROLE_PERMISSIONS: Record<string, OperatingModelPermission[]> = {
  transformation_office: [
    'portfolio.view',
    'initiatives.view_all',
    'initiatives.manage_all',
    'initiatives.manage_assigned',
    'initiatives.manage_workstream',
    'users.manage',
    'tenant_setup.manage',
    'financials.manage',
    'financials.manage_assigned',
    'benefits.validate',
    'benefits.realize',
    'shared_costs.manage',
    'governance.manage',
    'program_cadence.manage',
    'execution_evidence.manage',
    'execution_evidence.manage_assigned',
    'execution_evidence.manage_workstream',
  ],
  tenant_admin: [
    'portfolio.view',
    'initiatives.view_all',
    'users.manage',
    'tenant_setup.manage',
    'governance.manage',
  ],
  pmo_lead: [
    'portfolio.view',
    'initiatives.view_all',
    'governance.manage',
    'program_cadence.manage',
    'execution_evidence.manage',
  ],
  finance_lead: [
    'portfolio.view',
    'initiatives.view_all',
    'financials.manage',
    'benefits.validate',
    'benefits.realize',
    'shared_costs.manage',
  ],
  workstream_lead: [
    'portfolio.view',
    'initiatives.manage_workstream',
    'execution_evidence.manage_workstream',
  ],
  initiative_owner: [
    'initiatives.manage_assigned',
    'financials.manage_assigned',
    'execution_evidence.manage_assigned',
  ],
  business_benefit_owner: ['portfolio.view', 'initiatives.view_all', 'benefits.realize'],
  executive_sponsor: ['portfolio.view', 'initiatives.view_all'],
  viewer: ['portfolio.view', 'initiatives.view_all'],
};

export function hasOperatingModelPermission(
  role: string | null | undefined,
  permission: OperatingModelPermission,
): boolean {
  if (!role) return false;
  return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
}

export function operatingModelRoleLabel(role: string | null | undefined): string {
  return OPERATING_MODEL_ROLES.find(item => item.id === role)?.name
    ?? (role || 'unassigned').replace(/_/g, ' ');
}
