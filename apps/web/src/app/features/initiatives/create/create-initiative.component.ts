import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';

interface WorkstreamOption {
  id: string;
  name: string;
}

interface UserOption {
  id: string;
  display_name: string;
}

type CreationPath = 'chooser' | 'form' | 'upload' | 'ai';

@Component({
  selector: 'app-create-initiative',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  styles: [`
    :host { display: block; }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .animate-in { animation: fadeIn 0.3s ease both; }

    @keyframes slideUp {
      from { opacity: 0; transform: translateY(16px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .slide-up { animation: slideUp 0.35s ease both; }

    .path-card {
      cursor: pointer;
      transition: all 0.25s ease;
      position: relative;
      overflow: hidden;
    }
    .path-card::before {
      content: '';
      position: absolute;
      inset: 0;
      background: var(--t-accent-gradient);
      opacity: 0;
      transition: opacity 0.25s ease;
      border-radius: inherit;
    }
    .path-card:hover::before { opacity: 0.04; }
    .path-card:hover {
      border-color: var(--t-accent);
      box-shadow: 0 8px 24px var(--t-accent-ring);
      transform: translateY(-2px);
    }

    .field-label {
      display: block;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.375rem;
      color: var(--t-text-secondary);
    }

    .step-indicator {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .step-dot {
      width: 8px; height: 8px;
      border-radius: 50%;
      transition: all 0.2s ease;
    }
    .step-dot.active {
      background: var(--t-accent);
      box-shadow: 0 0 0 3px var(--t-accent-ring);
    }
    .step-dot.complete { background: var(--t-green); }
    .step-dot.pending {
      background: var(--t-border);
    }

    select {
      appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%236b7280' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 10px center;
      padding-right: 30px !important;
    }

    textarea { resize: vertical; min-height: 80px; }

    .upload-zone {
      border: 2px dashed var(--t-border);
      border-radius: 12px;
      padding: 3rem 2rem;
      text-align: center;
      transition: all 0.2s ease;
      cursor: pointer;
    }
    .upload-zone:hover,
    .upload-zone.dragover {
      border-color: var(--t-accent);
      background: var(--t-accent-soft);
    }
  `],
  template: `
<div class="min-h-screen" style="background:var(--t-bg)">
  <div class="max-w-4xl mx-auto px-8 py-8">

    <!-- BREADCRUMB -->
    <div class="flex items-center gap-2 mb-6 text-sm animate-in">
      <a routerLink="/initiatives/pipeline"
         class="transition-colors"
         style="color:var(--t-text-secondary)"
         aria-label="Back to pipeline">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m15 18-6-6 6-6"/>
        </svg>
      </a>
      <a routerLink="/initiatives/pipeline"
         style="color:var(--t-text-secondary)"
         class="hover:underline">Initiatives</a>
      <span style="color:var(--t-border)">/</span>
      <span style="color:var(--t-text-primary)" class="font-medium">New Initiative</span>
    </div>

    <!-- ═══════════════ PATH CHOOSER ═══════════════ -->
    <div *ngIf="currentPath === 'chooser'" class="slide-up">
      <h1 class="text-3xl font-bold tracking-tight mb-2"
          style="color:var(--t-text-primary)">
        Create Initiative<span style="color:var(--t-accent)">.</span>
      </h1>
      <p class="mb-8" style="color:var(--t-text-secondary)">
        Choose how you'd like to create your initiative.
      </p>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">

        <!-- Path A: Manual Form -->
        <div class="card path-card p-6" (click)="currentPath = 'form'"
             role="button" tabindex="0" aria-label="Create initiative manually"
             (keydown.enter)="currentPath = 'form'">
          <div class="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
               style="background:var(--t-accent-soft)">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
                 fill="none" stroke="var(--t-accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>
            </svg>
          </div>
          <h3 class="text-lg font-semibold mb-2" style="color:var(--t-text-primary)">
            Create Manually
          </h3>
          <p class="text-sm" style="color:var(--t-text-secondary)">
            Fill in the initiative details step by step. Define the scope, financials, and team.
          </p>
        </div>

        <!-- Path B: Excel Upload -->
        <div class="card path-card p-6" (click)="currentPath = 'upload'"
             role="button" tabindex="0" aria-label="Upload Excel template"
             (keydown.enter)="currentPath = 'upload'">
          <div class="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
               style="background:rgba(16,185,129,0.08)">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
                 fill="none" stroke="var(--t-green)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/>
              <line x1="12" x2="12" y1="3" y2="15"/>
            </svg>
          </div>
          <h3 class="text-lg font-semibold mb-2" style="color:var(--t-text-primary)">
            Upload Excel Template
          </h3>
          <p class="text-sm" style="color:var(--t-text-secondary)">
            Upload a pre-filled Transmuter Excel template with all initiative data.
          </p>
          <a href="/api/initiatives/template" class="text-xs mt-3 inline-block"
             style="color:var(--t-accent)" (click)="$event.stopPropagation()"
             aria-label="Download blank template">
            ↓ Download blank template
          </a>
        </div>
      </div>
    </div>

    <!-- ═══════════════ MANUAL FORM ═══════════════ -->
    <div *ngIf="currentPath === 'form'" class="slide-up">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-3xl font-bold tracking-tight"
              style="color:var(--t-text-primary)">
            New Initiative<span style="color:var(--t-accent)">.</span>
          </h1>
          <p class="text-sm mt-1" style="color:var(--t-text-secondary)">
            Step {{ formStep }} of 3 — {{ stepLabel() }}
          </p>
        </div>
        <div class="step-indicator">
          <div *ngFor="let s of [1,2,3]"
               class="step-dot"
               [class.active]="formStep === s"
               [class.complete]="formStep > s"
               [class.pending]="formStep < s">
          </div>
        </div>
      </div>

      <div class="card p-6">

        <!-- STEP 1: Basic Details -->
        <div *ngIf="formStep === 1" class="space-y-5 animate-in">
          <div>
            <label for="init-name" class="field-label">Initiative Name *</label>
            <input id="init-name" type="text" class="input-field"
                   [(ngModel)]="form.name" placeholder="e.g. HK Accounting System Integration & Automation"
                   aria-required="true">
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="init-workstream" class="field-label">Workstream</label>
              <select id="init-workstream" class="input-field" [(ngModel)]="form.workstream_id">
                <option value="">Select workstream</option>
                <option *ngFor="let ws of workstreams()" [value]="ws.id">{{ ws.name }}</option>
              </select>
            </div>
            <div>
              <label for="init-country" class="field-label">Country / Market</label>
              <input id="init-country" type="text" class="input-field"
                     [(ngModel)]="form.country" placeholder="e.g. HK, SG, AU">
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="init-type" class="field-label">Initiative Type</label>
              <select id="init-type" class="input-field" [(ngModel)]="form.type">
                <option value="">Select type</option>
                <option value="revenue_growth">Revenue Growth</option>
                <option value="cost_reduction">Cost Reduction</option>
                <option value="cost_avoidance">Cost Avoidance</option>
                <option value="compliance">Compliance</option>
                <option value="capability_building">Capability Building</option>
              </select>
            </div>
            <div>
              <label for="init-impact" class="field-label">Impact Type</label>
              <select id="init-impact" class="input-field" [(ngModel)]="form.impact_type">
                <option value="">Select impact</option>
                <option value="recurring">Recurring</option>
                <option value="one_off">One-off</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="init-priority" class="field-label">Priority</label>
              <select id="init-priority" class="input-field" [(ngModel)]="form.priority">
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div>
              <label for="init-tag" class="field-label">Tag</label>
              <select id="init-tag" class="input-field" [(ngModel)]="form.tag">
                <option value="">Select tag</option>
                <option value="automation">Automation</option>
                <option value="offshoring">Offshoring</option>
                <option value="commercial">Commercial</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
        </div>

        <!-- STEP 2: Description & Context -->
        <div *ngIf="formStep === 2" class="space-y-5 animate-in">
          <div>
            <label for="init-summary" class="field-label">Summary / Description</label>
            <textarea id="init-summary" class="input-field" rows="3"
                      [(ngModel)]="form.summary"
                      placeholder="End-to-end accounting process automation..."></textarea>
          </div>

          <div>
            <label for="init-value-logic" class="field-label">Value Logic / Main Assumptions</label>
            <textarea id="init-value-logic" class="input-field" rows="3"
                      [(ngModel)]="form.value_logic"
                      placeholder="25–30% productivity uplift through system integration..."></textarea>
          </div>

          <div>
            <label for="init-deps" class="field-label">Dependencies</label>
            <textarea id="init-deps" class="input-field" rows="2"
                      [(ngModel)]="form.dependencies_text"
                      placeholder="Any upstream or downstream dependencies..."></textarea>
          </div>
        </div>

        <!-- STEP 3: Ownership & Timeline -->
        <div *ngIf="formStep === 3" class="space-y-5 animate-in">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="init-owner" class="field-label">Market Owner</label>
              <select id="init-owner" class="input-field" [(ngModel)]="form.owner_id">
                <option value="">Select owner</option>
                <option *ngFor="let u of users()" [value]="u.id">{{ u.display_name }}</option>
              </select>
            </div>
            <div>
              <label for="init-group-owner" class="field-label">Group Owner</label>
              <select id="init-group-owner" class="input-field" [(ngModel)]="form.group_owner_id">
                <option value="">Select group owner</option>
                <option *ngFor="let u of users()" [value]="u.id">{{ u.display_name }}</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="init-start" class="field-label">Planned Start Date</label>
              <input id="init-start" type="date" class="input-field"
                     [(ngModel)]="form.planned_start">
            </div>
            <div>
              <label for="init-end" class="field-label">Planned Completion Date</label>
              <input id="init-end" type="date" class="input-field"
                     [(ngModel)]="form.planned_end">
            </div>
          </div>
        </div>

        <!-- NAVIGATION BUTTONS -->
        <div class="flex items-center justify-between mt-8 pt-5 border-t"
             style="border-color:var(--t-border)">
          <button *ngIf="formStep > 1" class="btn-secondary text-sm"
                  (click)="formStep = formStep - 1"
                  aria-label="Go to previous step">
            ← Back
          </button>
          <button *ngIf="formStep === 1" class="btn-ghost text-sm"
                  (click)="currentPath = 'chooser'"
                  aria-label="Return to path chooser">
            ← Change method
          </button>

          <div class="flex items-center gap-3">
            <button *ngIf="formStep < 3" class="btn-primary text-sm"
                    (click)="formStep = formStep + 1"
                    [disabled]="formStep === 1 && !form.name.trim()"
                    aria-label="Go to next step">
              Next →
            </button>
            <button *ngIf="formStep === 3" class="btn-primary text-sm"
                    (click)="submitForm()"
                    [disabled]="submitting()"
                    aria-label="Create initiative">
              <span *ngIf="!submitting()">Create Initiative</span>
              <span *ngIf="submitting()" class="flex items-center gap-2">
                <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.3"/>
                  <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
                </svg>
                Creating…
              </span>
            </button>
          </div>
        </div>
      </div>

      <!-- Error display -->
      <div *ngIf="error()" class="mt-4 p-4 rounded-lg text-sm"
           style="background:rgba(239,68,68,0.08);color:var(--t-red);border:1px solid rgba(239,68,68,0.2)">
        {{ error() }}
      </div>
    </div>

    <!-- ═══════════════ EXCEL UPLOAD ═══════════════ -->
    <div *ngIf="currentPath === 'upload'" class="slide-up">
      <h1 class="text-3xl font-bold tracking-tight mb-2"
          style="color:var(--t-text-primary)">
        Upload Initiative<span style="color:var(--t-accent)">.</span>
      </h1>
      <p class="mb-6" style="color:var(--t-text-secondary)">
        Upload a pre-filled Transmuter Excel template to create an initiative with all data.
      </p>

      <div class="card p-6">
        <div class="upload-zone"
             [class.dragover]="isDragOver"
             (dragover)="onDragOver($event)"
             (dragleave)="isDragOver = false"
             (drop)="onDrop($event)"
             (click)="fileInput.click()"
             role="button" tabindex="0"
             aria-label="Drop Excel file here or click to browse">
          <input #fileInput type="file" class="hidden"
                 accept=".xlsx,.xls"
                 (change)="onFileSelected($event)"
                 aria-hidden="true">
          <div class="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
               style="background:var(--t-accent-soft)">
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24"
                 fill="none" stroke="var(--t-accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/>
              <line x1="12" x2="12" y1="3" y2="15"/>
            </svg>
          </div>
          <p class="font-medium mb-1" style="color:var(--t-text-primary)">
            Drop your Excel file here
          </p>
          <p class="text-sm" style="color:var(--t-text-secondary)">
            or <span style="color:var(--t-accent)" class="underline">browse files</span>
            — .xlsx format only
          </p>
        </div>

        <div *ngIf="uploadedFileName()" class="mt-4 p-3 rounded-lg flex items-center justify-between"
             style="background:var(--t-surface-raised);border:1px solid var(--t-border)">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg flex items-center justify-center"
                 style="background:rgba(16,185,129,0.1)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                   stroke="var(--t-green)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 6 9 17l-5-5"/>
              </svg>
            </div>
            <span class="text-sm font-medium" style="color:var(--t-text-primary)">{{ uploadedFileName() }}</span>
          </div>
          <button class="btn-ghost text-xs" (click)="clearUpload()" aria-label="Remove uploaded file">✕</button>
        </div>

        <div class="flex items-center justify-between mt-6 pt-5 border-t"
             style="border-color:var(--t-border)">
          <button class="btn-ghost text-sm" (click)="currentPath = 'chooser'"
                  aria-label="Return to path chooser">
            ← Change method
          </button>
          <button class="btn-primary text-sm"
                  [disabled]="!uploadedFileName() || submitting()"
                  (click)="submitUpload()"
                  aria-label="Upload and create initiative">
            <span *ngIf="!submitting()">Upload & Create</span>
            <span *ngIf="submitting()">Uploading…</span>
          </button>
        </div>
      </div>

      <div *ngIf="error()" class="mt-4 p-4 rounded-lg text-sm"
           style="background:rgba(239,68,68,0.08);color:var(--t-red);border:1px solid rgba(239,68,68,0.2)">
        {{ error() }}
      </div>
    </div>

  </div>
</div>
  `,
})
export class CreateInitiativeComponent {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);

  currentPath: CreationPath = 'chooser';
  formStep = 1;
  isDragOver = false;

  readonly submitting = signal(false);
  readonly error = signal<string | null>(null);
  readonly workstreams = signal<WorkstreamOption[]>([]);
  readonly users = signal<UserOption[]>([]);
  readonly uploadedFileName = signal<string | null>(null);

  private uploadedFile: File | null = null;

  form = {
    name: '',
    workstream_id: '',
    owner_id: '',
    group_owner_id: '',
    type: '',
    impact_type: '',
    country: '',
    tag: '',
    priority: 'medium',
    summary: '',
    value_logic: '',
    dependencies_text: '',
    planned_start: '',
    planned_end: '',
  };

  constructor() {
    this.loadDropdownData();
  }

  stepLabel(): string {
    return this.formStep === 1 ? 'Basic Details'
         : this.formStep === 2 ? 'Description & Context'
         : 'Ownership & Timeline';
  }

  /** Load workstreams and users for dropdowns */
  private loadDropdownData(): void {
    this.api.get<{ data: WorkstreamOption[] }>('/workstreams').subscribe({
      next: r => this.workstreams.set(r.data ?? []),
      error: () => {},  // graceful — dropdowns remain empty
    });
    this.api.get<{ data: UserOption[] }>('/users').subscribe({
      next: r => this.users.set(r.data ?? []),
      error: () => {},
    });
  }

  /** Submit the manual form */
  submitForm(): void {
    if (!this.form.name.trim()) {
      this.error.set('Initiative name is required.');
      return;
    }

    this.submitting.set(true);
    this.error.set(null);

    // Build payload — only send non-empty fields
    const payload: Record<string, unknown> = { name: this.form.name.trim() };
    if (this.form.workstream_id) payload['workstream_id'] = this.form.workstream_id;
    if (this.form.owner_id) payload['owner_id'] = this.form.owner_id;
    if (this.form.group_owner_id) payload['group_owner_id'] = this.form.group_owner_id;
    if (this.form.type) payload['type'] = this.form.type;
    if (this.form.impact_type) payload['impact_type'] = this.form.impact_type;
    if (this.form.country) payload['country'] = this.form.country;
    if (this.form.tag) payload['tag'] = this.form.tag;
    if (this.form.priority) payload['priority'] = this.form.priority;
    if (this.form.summary) payload['summary'] = this.form.summary;
    if (this.form.value_logic) payload['value_logic'] = this.form.value_logic;
    if (this.form.dependencies_text) payload['dependencies_text'] = this.form.dependencies_text;
    if (this.form.planned_start) payload['planned_start'] = this.form.planned_start;
    if (this.form.planned_end) payload['planned_end'] = this.form.planned_end;

    this.api.post<{ id: string }>('/initiatives', payload).subscribe({
      next: result => {
        this.submitting.set(false);
        this.router.navigate(['/initiatives', result.id]);
      },
      error: err => {
        this.submitting.set(false);
        this.error.set(err?.error?.detail ?? 'Failed to create initiative. Please try again.');
      },
    });
  }

  /** File upload handlers */
  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
    const file = event.dataTransfer?.files?.[0];
    if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) {
      this.uploadedFile = file;
      this.uploadedFileName.set(file.name);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      this.uploadedFile = file;
      this.uploadedFileName.set(file.name);
    }
  }

  clearUpload(): void {
    this.uploadedFile = null;
    this.uploadedFileName.set(null);
  }

  submitUpload(): void {
    if (!this.uploadedFile) return;

    this.submitting.set(true);
    this.error.set(null);

    const formData = new FormData();
    formData.append('file', this.uploadedFile);

    // Note: Using HttpClient directly since ApiService doesn't handle FormData
    // The upload endpoint will be POST /initiatives/import
    this.api.post<{ id: string }>('/initiatives/import', formData).subscribe({
      next: result => {
        this.submitting.set(false);
        this.router.navigate(['/initiatives', result.id]);
      },
      error: err => {
        this.submitting.set(false);
        this.error.set(err?.error?.detail ?? 'Failed to parse template. Please check the file format.');
      },
    });
  }
}
