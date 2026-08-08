import { TestBed } from '@angular/core/testing';
import { describe, expect, it, vi } from 'vitest';
import { RoadmapGanttComponent } from './roadmap-gantt.component';
import { RoadmapInitiative, RoadmapMilestone } from './roadmap.models';

const initiative: RoadmapInitiative = {
  id: 'initiative-1',
  name: 'ERP modernisation',
  initiative_code: 'ERP-01',
  workstream_id: 'workstream-1',
  workstream_name: 'Technology',
};

const milestone = (
  id: string,
  plannedStart: string | null,
  plannedEnd: string | null,
): RoadmapMilestone => ({
  id,
  initiative_id: initiative.id,
  initiative_name: initiative.name,
  initiative_code: initiative.initiative_code,
  workstream_id: initiative.workstream_id,
  workstream_name: initiative.workstream_name,
  name: id === 'point' ? 'Design approval' : 'Pilot rollout',
  description: null,
  owner_id: null,
  owner_name: 'Delivery lead',
  priority: 'high',
  status: id === 'point' ? 'complete' : 'in_progress',
  sort_order: 0,
  planned_start: plannedStart,
  actual_start: null,
  planned_end: plannedEnd,
  actual_end: null,
  pressure_score: '2.0',
  pressure_level: 'green',
  dependency_count: 0,
});

describe('RoadmapGanttComponent', () => {
  it('renders ranged and completion-only milestones as selectable timeline items', async () => {
    await TestBed.configureTestingModule({ imports: [RoadmapGanttComponent] }).compileComponents();
    const fixture = TestBed.createComponent(RoadmapGanttComponent);
    fixture.componentRef.setInput('initiatives', [initiative]);
    fixture.componentRef.setInput('milestones', [
      milestone('range', '2026-01-01', '2026-04-30'),
      milestone('point', null, '2026-05-15'),
    ]);
    fixture.componentRef.setInput('dependencies', [{
      id: 'dependency-1',
      source: 'range',
      target: 'point',
      status: 'on_track',
      dependency_type: 'finish_to_start',
      lag_days: 0,
    }]);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const element = fixture.nativeElement as HTMLElement;
    const plottedItems = element.querySelectorAll<HTMLButtonElement>('[data-roadmap-milestone]');
    expect(plottedItems).toHaveLength(2);
    expect(element.querySelector('[data-milestone-id="point"]')).not.toBeNull();
    expect(element.querySelectorAll('path.roadmap-link')).toHaveLength(1);

    const selected = vi.fn();
    fixture.componentInstance.milestoneSelected.subscribe(selected);
    plottedItems[0].click();
    expect(selected).toHaveBeenCalledWith('range');
  });
});
