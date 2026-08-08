import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import {
  Gantt,
  escapeHTML,
  type GanttData,
  type GanttStatic,
  type Link,
  type Task,
  type TaskInput,
} from 'dhtmlx-gantt';
import 'dhtmlx-gantt/codebase/dhtmlxgantt.css';
import {
  RoadmapDependency,
  RoadmapInitiative,
  RoadmapLinkMode,
  RoadmapMilestone,
  RoadmapZoom,
} from './roadmap.models';

type GanttTaskInput = TaskInput & {
  id: string;
  text: string;
  parent: string | number;
  status?: string;
  owner?: string;
  initiativeCode?: string;
  isRoadmapMilestone?: boolean;
  inTrace?: boolean;
};

@Component({
  selector: 'app-roadmap-gantt',
  standalone: true,
  template: `<div #container class="roadmap-gantt-host" data-testid="roadmap-gantt" aria-label="Portfolio milestone Gantt chart"></div>`,
  styles: [`
    :host { display: block; min-height: 620px; }
    .roadmap-gantt-host { width: 100%; height: min(72vh, 820px); min-height: 620px; }
  `],
})
export class RoadmapGanttComponent implements AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('container', { static: true }) private container!: ElementRef<HTMLDivElement>;
  @Input() milestones: RoadmapMilestone[] = [];
  @Input() initiatives: RoadmapInitiative[] = [];
  @Input() dependencies: RoadmapDependency[] = [];
  @Input() zoom: RoadmapZoom = 'quarter';
  @Input() linkMode: RoadmapLinkMode = 'all';
  @Input() selectedMilestoneId: string | null = null;
  @Output() milestoneSelected = new EventEmitter<string>();

  private gantt: GanttStatic | null = null;
  private initialized = false;
  private eventIds: string[] = [];

  ngAfterViewInit(): void {
    this.initialize();
    this.renderData();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.initialized) return;
    if (changes['zoom']) this.applyZoom();
    this.renderData();
  }

  ngOnDestroy(): void {
    if (!this.gantt) return;
    this.eventIds.forEach(id => this.gantt?.detachEvent(id));
    this.gantt.destructor();
    this.gantt = null;
  }

  fitAll(): void {
    if (!this.gantt) return;
    this.gantt.config.start_date = undefined;
    this.gantt.config.end_date = undefined;
    this.gantt.render();
  }

  showToday(): void {
    this.gantt?.showDate(new Date());
  }

  private initialize(): void {
    this.gantt = Gantt.getGanttInstance();
    this.gantt.plugins({ tooltip: true, keyboard_navigation: true, marker: true });
    this.gantt.config.readonly = true;
    this.gantt.config.drag_links = false;
    this.gantt.config.drag_move = false;
    this.gantt.config.drag_progress = false;
    this.gantt.config.drag_resize = false;
    this.gantt.config.details_on_dblclick = false;
    this.gantt.config.show_quick_info = false;
    this.gantt.config.open_tree_initially = true;
    this.gantt.config.smart_rendering = true;
    this.gantt.config.row_height = 38;
    this.gantt.config['task_height'] = 16;
    this.gantt.config.grid_width = 520;
    this.gantt.config.min_grid_column_width = 70;
    this.gantt.config.date_format = '%Y-%m-%d';
    this.gantt.config.columns = [
      { name: 'text', label: 'Initiative / milestone', tree: true, width: 260, resize: true },
      { name: 'owner', label: 'Owner', align: 'left', width: 105, resize: true },
      { name: 'status', label: 'Status', align: 'left', width: 82, resize: true },
      { name: 'start_date', label: 'Start', align: 'center', width: 72 },
    ];
    this.gantt.templates.grid_folder = () => '';
    this.gantt.templates.grid_file = () => '';
    this.gantt.templates.grid_row_class = (_start: Date, _end: Date, task: Task) =>
      task['inTrace'] === false ? 'roadmap-dimmed' : '';
    this.gantt.templates.task_class = (_start: Date, _end: Date, task: Task) => {
      const classes = [`roadmap-status-${String(task['status'] || 'not_started')}`];
      if (task['isRoadmapMilestone']) classes.push('roadmap-window');
      if (task['inTrace'] === false) classes.push('roadmap-dimmed');
      if (String(task.id) === this.selectedMilestoneId) classes.push('roadmap-selected');
      return classes.join(' ');
    };
    this.gantt.templates.link_class = (link: Link) => {
      const status = String(link['status'] || 'on_track');
      return `roadmap-link-${status}`;
    };
    this.gantt.templates.task_text = (_start: Date, _end: Date, task: Task) =>
      task.type === this.gantt?.config.types.project ? '' : escapeHTML(String(task.text || ''));
    this.gantt.templates.tooltip_text = (_start: Date, _end: Date, task: Task) => {
      const gantt = this.gantt;
      if (!gantt) return '';
      const start = task.start_date || new Date();
      const end = task.end_date || start;
      const dates = task.type === gantt.config.types.milestone
        ? gantt.templates.tooltip_date_format(start)
        : `${gantt.templates.tooltip_date_format(start)} – ${gantt.templates.tooltip_date_format(end)}`;
      return `<strong>${escapeHTML(String(task.text || ''))}</strong><br>${escapeHTML(dates)}<br>${escapeHTML(String(task['owner'] || 'Owner not assigned'))}`;
    };
    this.applyZoom();
    this.eventIds.push(
      this.gantt.attachEvent('onTaskClick', (id: string | number) => {
        const task = this.gantt?.getTask(id);
        if (task?.['isRoadmapMilestone']) this.milestoneSelected.emit(String(id));
        return true;
      }),
    );
    this.gantt.init(this.container.nativeElement);
    this.gantt.addMarker({
      start_date: new Date(),
      css: 'today',
      text: 'Today',
      title: 'Today',
    });
    this.initialized = true;
  }

  private applyZoom(): void {
    if (!this.gantt) return;
    const scaleConfig: Record<RoadmapZoom, { min_column_width: number; scales: Array<{ unit: string; step: number; format: string }> }> = {
      year: {
        min_column_width: 70,
        scales: [{ unit: 'year', step: 1, format: '%Y' }, { unit: 'quarter', step: 1, format: 'Q%q' }],
      },
      quarter: {
        min_column_width: 54,
        scales: [{ unit: 'year', step: 1, format: '%Y' }, { unit: 'month', step: 1, format: '%M' }],
      },
      month: {
        min_column_width: 32,
        scales: [{ unit: 'month', step: 1, format: '%F %Y' }, { unit: 'week', step: 1, format: 'W%W' }],
      },
      week: {
        min_column_width: 30,
        scales: [{ unit: 'month', step: 1, format: '%F %Y' }, { unit: 'day', step: 1, format: '%d' }],
      },
    };
    Object.assign(this.gantt.config, scaleConfig[this.zoom]);
    if (this.initialized) this.gantt.render();
  }

  private renderData(): void {
    if (!this.gantt || !this.initialized) return;
    const visibleIds = new Set(this.milestones.map(item => item.id));
    const candidateLinks = this.dependencies.filter(link => visibleIds.has(link.source) && visibleIds.has(link.target));
    const traceIds = this.traceIds(candidateLinks);
    const filteredLinks = this.filterLinks(candidateLinks, traceIds);
    const tasks = this.buildTasks(traceIds);
    const links = filteredLinks.map(link => ({
      id: link.id,
      source: link.source,
      target: link.target,
      type: this.linkType(link.dependency_type),
      lag: link.lag_days,
      status: link.status,
      readonly: true,
    }));
    const data = { data: tasks, links } as unknown as GanttData;
    this.gantt.clearAll();
    this.gantt.parse(data);
    if (this.selectedMilestoneId && this.gantt.isTaskExists(this.selectedMilestoneId)) {
      this.gantt.selectTask(this.selectedMilestoneId);
    }
  }

  private buildTasks(traceIds: Set<string> | null): GanttTaskInput[] {
    const tasks: GanttTaskInput[] = [];
    const initiativeIds = new Set(this.milestones.map(item => item.initiative_id));
    const visibleInitiatives = this.initiatives.filter(item => initiativeIds.has(item.id));
    const workstreams = new Map<string, string>();
    visibleInitiatives.forEach(item => {
      const id = item.workstream_id || `name:${item.workstream_name || 'unassigned'}`;
      workstreams.set(id, item.workstream_name || 'Unassigned workstream');
    });
    [...workstreams.entries()].sort((a, b) => a[1].localeCompare(b[1])).forEach(([id, name]) => {
      tasks.push({ id: `ws:${id}`, text: name, parent: 0, type: 'project', open: true, readonly: true });
    });
    visibleInitiatives.forEach(item => {
      const workstreamId = item.workstream_id || `name:${item.workstream_name || 'unassigned'}`;
      tasks.push({
        id: `init:${item.id}`,
        text: `${item.initiative_code ? `${item.initiative_code} · ` : ''}${item.name}`,
        parent: `ws:${workstreamId}`,
        type: 'project',
        open: true,
        readonly: true,
        initiativeCode: item.initiative_code || '',
      });
    });
    this.milestones
      .filter(item => !!item.planned_end)
      .sort((a, b) => (a.planned_start || a.planned_end || '').localeCompare(b.planned_start || b.planned_end || ''))
      .forEach(item => {
        const start = item.planned_start || item.planned_end as string;
        const end = item.planned_end as string;
        const isPoint = !item.planned_start || start === end;
        tasks.push({
          id: item.id,
          text: item.name,
          parent: `init:${item.initiative_id}`,
          start_date: start,
          end_date: end,
          duration: isPoint ? 0 : undefined,
          type: isPoint ? 'milestone' : 'task',
          open: true,
          readonly: true,
          status: item.status,
          owner: item.owner_name || 'Unassigned',
          initiativeCode: item.initiative_code || '',
          isRoadmapMilestone: true,
          inTrace: traceIds ? traceIds.has(item.id) : undefined,
        });
      });
    return tasks;
  }

  private filterLinks(links: RoadmapDependency[], traceIds: Set<string> | null): RoadmapDependency[] {
    if (this.linkMode === 'hidden') return [];
    if (this.linkMode === 'blocking') return links.filter(link => link.status === 'blocking' || link.status === 'at_risk');
    if (this.linkMode === 'trace') {
      if (!this.selectedMilestoneId || !traceIds) return [];
      return links.filter(link => traceIds.has(link.source) && traceIds.has(link.target));
    }
    return links;
  }

  private traceIds(links: RoadmapDependency[]): Set<string> | null {
    if (this.linkMode !== 'trace' || !this.selectedMilestoneId) return null;
    const traced = new Set<string>([this.selectedMilestoneId]);
    const queue = [this.selectedMilestoneId];
    while (queue.length) {
      const current = queue.shift() as string;
      links.forEach(link => {
        const neighbor = link.source === current ? link.target : link.target === current ? link.source : null;
        if (neighbor && !traced.has(neighbor)) {
          traced.add(neighbor);
          queue.push(neighbor);
        }
      });
    }
    return traced;
  }

  private linkType(type: RoadmapDependency['dependency_type']): string {
    return {
      finish_to_start: '0',
      start_to_start: '1',
      finish_to_finish: '2',
      start_to_finish: '3',
    }[type];
  }
}
