export type DependencyStatus = 'blocking' | 'at_risk' | 'resolved' | 'on_track';
export type DependencyType =
  | 'finish_to_start'
  | 'start_to_start'
  | 'finish_to_finish'
  | 'start_to_finish';

export interface RoadmapRange {
  earliest_start: string | null;
  latest_end: string | null;
}

export interface RoadmapInitiative {
  id: string;
  name: string;
  initiative_code: string | null;
  workstream_id: string | null;
  workstream_name: string | null;
}

export interface RoadmapMilestone {
  id: string;
  initiative_id: string;
  initiative_name: string | null;
  initiative_code: string | null;
  workstream_id: string | null;
  workstream_name: string | null;
  name: string;
  description: string | null;
  owner_id: string | null;
  owner_name: string | null;
  priority: string;
  status: string;
  sort_order: number;
  planned_start: string | null;
  actual_start: string | null;
  planned_end: string | null;
  actual_end: string | null;
  pressure_score: string | null;
  pressure_level: string | null;
  dependency_count: number;
}

export interface RoadmapDependency {
  id: string;
  source: string;
  target: string;
  status: DependencyStatus;
  dependency_type: DependencyType;
  lag_days: number;
}

export interface RoadmapStats {
  milestones: number;
  initiatives: number;
  dependencies: number;
  blocking_links: number;
  missing_dates: number;
}

export interface PortfolioRoadmapResponse {
  range: RoadmapRange;
  initiatives: RoadmapInitiative[];
  milestones: RoadmapMilestone[];
  dependencies: RoadmapDependency[];
  stats: RoadmapStats;
}

export type RoadmapZoom = 'year' | 'quarter' | 'month' | 'week';
export type RoadmapLinkMode = 'all' | 'blocking' | 'trace' | 'hidden';
