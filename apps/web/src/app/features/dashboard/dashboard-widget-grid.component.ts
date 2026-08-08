import {
  AfterContentInit,
  Component,
  ContentChildren,
  Input,
  QueryList,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';
import type {
  DashboardBreakpoint,
  DashboardKey,
  DashboardWidgetLayout,
  DashboardWidgetSize,
} from './dashboard-layout.models';
import { DashboardLayoutService } from './dashboard-layout.service';
import { DashboardWidgetDirective } from './dashboard-widget.directive';

const SIZE_SEQUENCE: DashboardWidgetSize[] = ['small', 'medium', 'wide', 'full'];

@Component({
  selector: 'app-dashboard-widget-grid',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="mb-5 border-y border-[var(--t-border)] bg-[var(--t-surface)] px-4 py-3" aria-label="Dashboard layout controls">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="text-[10px] font-black uppercase tracking-[0.16em] text-[var(--t-text-tertiary)]">Dashboard layout</p>
          <p class="mt-1 text-xs text-[var(--t-text-secondary)]">
            {{ sourceLabel() }} · {{ editMode() ? 'Drag cards or use the move and size controls.' : 'Your saved view is active.' }}
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          @if (!editMode()) {
            <button type="button" class="btn-secondary text-xs" (click)="beginEditing()" aria-label="Customize dashboard layout">
              Customize layout
            </button>
          } @else {
            <button type="button" class="btn-secondary text-xs" (click)="cancelEditing()" aria-label="Cancel dashboard layout changes">Cancel</button>
            <button type="button" class="btn-secondary text-xs" (click)="resetLayout()" [disabled]="saving()" aria-label="Reset dashboard layout">Reset</button>
            @if (canPublish()) {
              <select class="input-field py-2 text-xs" [value]="publishRole()" (change)="setPublishRole($event)" aria-label="Role for dashboard default">
                @for (role of publishRoles; track role.key) {<option [value]="role.key">{{ role.label }}</option>}
              </select>
              <button type="button" class="btn-secondary text-xs" (click)="saveLayout(true)" [disabled]="saving()" aria-label="Publish layout as role default">Publish role default</button>
            }
            <button type="button" class="btn-primary text-xs" (click)="saveLayout(false)" [disabled]="saving()" aria-label="Save personal dashboard layout">
              {{ saving() ? 'Saving…' : 'Save my layout' }}
            </button>
          }
        </div>
      </div>
      @if (message()) {
        <p class="mt-3 text-xs font-semibold" [ngClass]="isError() ? 'text-red-600' : 'text-[var(--t-accent)]'" role="status">{{ message() }}</p>
      }
    </section>

    <div class="dashboard-widget-grid" [class.is-editing]="editMode()">
      @for (item of visibleLayout(); track item.widget_key; let index = $index) {
        @if (definition(item.widget_key); as definition) {
          <article
            class="dashboard-widget"
            [class.dashboard-widget--small]="item.size === 'small'"
            [class.dashboard-widget--medium]="item.size === 'medium'"
            [class.dashboard-widget--wide]="item.size === 'wide'"
            [class.dashboard-widget--full]="item.size === 'full'"
            [class.dashboard-widget--dragging]="draggedKey() === item.widget_key"
            [attr.draggable]="editMode()"
            [attr.data-widget-key]="item.widget_key"
            (dragstart)="startDrag(item.widget_key)"
            (dragover)="allowDrop($event)"
            (drop)="dropOn(item.widget_key)"
            (dragend)="draggedKey.set(null)">
            @if (editMode()) {
              <header class="dashboard-widget-toolbar">
                <div class="min-w-0">
                  <p class="truncate text-xs font-black uppercase tracking-wider text-[var(--t-text-primary)]">{{ definition.widgetTitle }}</p>
                  <p class="truncate text-[10px] text-[var(--t-text-tertiary)]">{{ sizeLabel(item.size) }}{{ definition.widgetRequired ? ' · Required' : '' }}</p>
                </div>
                <div class="flex items-center gap-1">
                  <button type="button" class="widget-control" (click)="move(index, -1)" [disabled]="index === 0" [attr.aria-label]="'Move ' + definition.widgetTitle + ' earlier'">←</button>
                  <button type="button" class="widget-control" (click)="move(index, 1)" [disabled]="index === visibleLayout().length - 1" [attr.aria-label]="'Move ' + definition.widgetTitle + ' later'">→</button>
                  <button type="button" class="widget-control min-w-16" (click)="cycleSize(item.widget_key)" [attr.aria-label]="'Resize ' + definition.widgetTitle">Resize</button>
                  @if (!definition.widgetRequired) {
                    <button type="button" class="widget-control" (click)="hide(item.widget_key)" [attr.aria-label]="'Hide ' + definition.widgetTitle">×</button>
                  }
                </div>
              </header>
            }
            <ng-container [ngTemplateOutlet]="definition.template" />
          </article>
        }
      }
    </div>

    @if (editMode() && hiddenDefinitions().length) {
      <section class="mt-5 border border-dashed border-[var(--t-border-strong)] bg-[var(--t-surface-muted)] p-4" aria-label="Hidden dashboard widgets">
        <p class="text-[10px] font-black uppercase tracking-[0.16em] text-[var(--t-text-tertiary)]">Hidden widgets</p>
        <div class="mt-3 flex flex-wrap gap-2">
          @for (definition of hiddenDefinitions(); track definition.key) {
            <button type="button" class="btn-secondary text-xs" (click)="show(definition.key)">Add {{ definition.widgetTitle }}</button>
          }
        </div>
      </section>
    }
  `,
  styles: [`
    .dashboard-widget-grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 1.5rem; align-items: start; }
    .dashboard-widget { grid-column: span 6; min-width: 0; }
    .dashboard-widget--small { grid-column: span 3; }
    .dashboard-widget--medium { grid-column: span 6; }
    .dashboard-widget--wide { grid-column: span 8; }
    .dashboard-widget--full { grid-column: 1 / -1; }
    .dashboard-widget-toolbar { display: flex; align-items: center; justify-content: space-between; gap: .75rem; border: 1px solid var(--t-border-strong); border-bottom: 0; background: var(--t-surface-muted); padding: .55rem .75rem; cursor: grab; }
    .widget-control { min-height: 2rem; min-width: 2rem; border: 1px solid var(--t-border-strong); background: var(--t-surface); color: var(--t-text-primary); padding: 0 .45rem; font-size: .7rem; font-weight: 800; }
    .widget-control:hover:not(:disabled) { border-color: var(--t-accent); color: var(--t-accent); }
    .widget-control:disabled { opacity: .35; cursor: not-allowed; }
    .dashboard-widget--dragging { opacity: .45; }
    @media (max-width: 1023px) { .dashboard-widget--small { grid-column: span 6; } .dashboard-widget--wide { grid-column: 1 / -1; } }
    @media (max-width: 767px) { .dashboard-widget { grid-column: 1 / -1; } }
  `],
})
export class DashboardWidgetGridComponent implements AfterContentInit {
  private readonly layouts = inject(DashboardLayoutService);
  private readonly auth = inject(AuthService);

  @Input({ required: true }) dashboardKey: DashboardKey = 'operational';
  @Input() breakpoint: DashboardBreakpoint = 'desktop';
  @ContentChildren(DashboardWidgetDirective) definitions!: QueryList<DashboardWidgetDirective>;

  protected readonly layout = signal<DashboardWidgetLayout[]>([]);
  protected readonly editMode = signal(false);
  protected readonly saving = signal(false);
  protected readonly message = signal('');
  protected readonly isError = signal(false);
  protected readonly source = signal<'personal' | 'tenant' | 'system'>('system');
  protected readonly draggedKey = signal<string | null>(null);
  protected readonly publishRole = signal('viewer');
  protected readonly publishRoles = [
    { key: 'transformation_office', label: 'Transformation Office' },
    { key: 'tenant_admin', label: 'Tenant Administrator' },
    { key: 'pmo_lead', label: 'PMO Lead' },
    { key: 'finance_lead', label: 'Finance Lead' },
    { key: 'workstream_lead', label: 'Workstream Lead' },
    { key: 'initiative_owner', label: 'Initiative Owner' },
    { key: 'business_benefit_owner', label: 'Business Benefit Owner' },
    { key: 'executive_sponsor', label: 'Executive Sponsor' },
    { key: 'viewer', label: 'Viewer' },
  ];
  private snapshot: DashboardWidgetLayout[] = [];

  protected readonly visibleLayout = computed(() => this.layout().filter(item => item.visible).sort((a, b) => a.order - b.order));
  protected readonly hiddenDefinitions = computed(() => {
    const visible = new Set(this.visibleLayout().map(item => item.widget_key));
    return this.definitionList().filter(definition => !visible.has(definition.key));
  });
  protected readonly sourceLabel = computed(() => ({
    personal: 'Personal layout',
    tenant: 'Role default layout',
    system: 'Standard layout',
  })[this.source()]);
  protected readonly canPublish = computed(() => ['transformation_office', 'tenant_admin'].includes(this.auth.getRole() || ''));

  ngAfterContentInit(): void {
    this.publishRole.set(this.auth.getRole() || 'viewer');
    this.layouts.getLayout(this.dashboardKey, this.breakpoint).subscribe({
      next: response => {
        this.source.set(response.source);
        this.layout.set(this.normalize(response.widgets || []));
      },
      error: () => {
        this.layout.set(this.defaultLayout());
        this.setMessage('The saved layout could not be loaded. The standard layout is shown.', true);
      },
    });
  }

  protected definition(key: string): DashboardWidgetDirective | undefined {
    return this.definitionList().find(item => item.key === key);
  }

  protected beginEditing(): void {
    this.snapshot = this.clone(this.layout());
    this.editMode.set(true);
    this.setMessage('', false);
  }

  protected cancelEditing(): void {
    this.layout.set(this.clone(this.snapshot));
    this.editMode.set(false);
    this.setMessage('', false);
  }

  protected startDrag(key: string): void {
    if (this.editMode()) this.draggedKey.set(key);
  }

  protected allowDrop(event: DragEvent): void {
    if (this.editMode()) event.preventDefault();
  }

  protected dropOn(targetKey: string): void {
    const sourceKey = this.draggedKey();
    if (!sourceKey || sourceKey === targetKey) return;
    const items = this.visibleLayout();
    const sourceIndex = items.findIndex(item => item.widget_key === sourceKey);
    const targetIndex = items.findIndex(item => item.widget_key === targetKey);
    if (sourceIndex < 0 || targetIndex < 0) return;
    const reordered = [...items];
    const [moved] = reordered.splice(sourceIndex, 1);
    reordered.splice(targetIndex, 0, moved);
    this.replaceVisible(reordered);
    this.draggedKey.set(null);
  }

  protected move(index: number, delta: number): void {
    const items = this.visibleLayout();
    const next = index + delta;
    if (next < 0 || next >= items.length) return;
    [items[index], items[next]] = [items[next], items[index]];
    this.replaceVisible(items);
  }

  protected cycleSize(key: string): void {
    this.layout.update(items => items.map(item => {
      if (item.widget_key !== key) return item;
      const next = (SIZE_SEQUENCE.indexOf(item.size) + 1) % SIZE_SEQUENCE.length;
      return { ...item, size: SIZE_SEQUENCE[next] };
    }));
  }

  protected hide(key: string): void {
    this.layout.update(items => items.map(item => item.widget_key === key ? { ...item, visible: false } : item));
  }

  protected show(key: string): void {
    this.layout.update(items => items.map(item => item.widget_key === key ? { ...item, visible: true } : item));
  }

  protected saveLayout(publishAsTenantDefault: boolean): void {
    this.saving.set(true);
    this.layouts.saveLayout(this.dashboardKey, {
      breakpoint: this.breakpoint,
      widgets: this.renumber(this.layout()),
      publish_as_tenant_default: publishAsTenantDefault,
      role_key: publishAsTenantDefault ? this.publishRole() : undefined,
    }).subscribe({
      next: response => {
        this.layout.set(this.normalize(response.widgets || []));
        this.source.set(response.source);
        this.editMode.set(false);
        this.saving.set(false);
        this.setMessage(publishAsTenantDefault ? 'Role default published.' : 'Personal layout saved.', false);
      },
      error: () => {
        this.saving.set(false);
        this.setMessage('The layout could not be saved. Try again.', true);
      },
    });
  }

  protected resetLayout(): void {
    this.saving.set(true);
    this.layouts.resetLayout(this.dashboardKey, this.breakpoint).subscribe({
      next: response => {
        this.layout.set(this.normalize(response.widgets || []));
        this.source.set(response.source);
        this.snapshot = this.clone(this.layout());
        this.saving.set(false);
        this.setMessage('Personal layout reset.', false);
      },
      error: () => {
        this.saving.set(false);
        this.setMessage('The layout could not be reset. Try again.', true);
      },
    });
  }

  protected sizeLabel(size: DashboardWidgetSize): string {
    return `${size.charAt(0).toUpperCase()}${size.slice(1)} width`;
  }

  protected setPublishRole(event: Event): void {
    this.publishRole.set((event.target as HTMLSelectElement).value);
  }

  private definitionList(): DashboardWidgetDirective[] {
    return this.definitions?.toArray() || [];
  }

  private defaultLayout(): DashboardWidgetLayout[] {
    return this.definitionList().map((definition, index) => ({
      widget_key: definition.key,
      order: (index + 1) * 10,
      size: definition.widgetDefaultSize,
      visible: true,
    }));
  }

  private normalize(received: DashboardWidgetLayout[]): DashboardWidgetLayout[] {
    const known = new Map(received.map(item => [item.widget_key, item]));
    const items = this.definitionList().map((definition, index) => {
      const item = known.get(definition.key);
      return item ? { ...item, visible: definition.widgetRequired || item.visible } : {
        widget_key: definition.key,
        order: (received.length + index + 1) * 10,
        size: definition.widgetDefaultSize,
        visible: true,
      };
    }).sort((a, b) => a.order - b.order);
    return this.renumber(this.pinRequired(items));
  }

  private replaceVisible(visible: DashboardWidgetLayout[]): void {
    const hidden = this.layout().filter(item => !item.visible);
    this.layout.set(this.renumber([...this.pinRequired(visible), ...hidden]));
  }

  private pinRequired(items: DashboardWidgetLayout[]): DashboardWidgetLayout[] {
    const required = items.filter(item => this.definition(item.widget_key)?.widgetRequired);
    const supporting = items.filter(item => !this.definition(item.widget_key)?.widgetRequired);
    return [...required, ...supporting];
  }

  private renumber(items: DashboardWidgetLayout[]): DashboardWidgetLayout[] {
    return items.map((item, index) => ({ ...item, order: (index + 1) * 10 }));
  }

  private clone(items: DashboardWidgetLayout[]): DashboardWidgetLayout[] {
    return items.map(item => ({ ...item }));
  }

  private setMessage(message: string, isError: boolean): void {
    this.message.set(message);
    this.isError.set(isError);
  }
}
