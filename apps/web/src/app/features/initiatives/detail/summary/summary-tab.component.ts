import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';

@Component({
  selector: 'app-summary-tab',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-8 animate-fade-in">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-xl font-bold text-[var(--t-text-primary)]">Summary & Results<span class="text-[var(--t-accent)]">.</span></h2>
          <p class="text-xs font-semibold uppercase tracking-wider text-[var(--t-text-secondary)]">Closure narrative and value realization</p>
        </div>
        <span class="px-3 py-1 rounded-lg border text-[10px] font-black uppercase tracking-widest"
              style="color:var(--t-accent);border-color:var(--t-border);background:var(--t-accent-soft)">
          {{ summary()?.draft_status || 'draft' }}
        </span>
      </div>
      
      <!-- Value Realization Hero -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="card p-8 bg-gradient-to-br from-[var(--t-surface)] to-[var(--t-surface-raised)] border-l-4 border-[var(--t-accent)]">
          <p class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest mb-2">Total Planned Value</p>
          <h2 class="text-4xl font-black text-[var(--t-text-primary)]">
            {{ formatCurrency(summary()?.planned_value) }}
          </h2>
          <p class="text-xs font-medium text-[var(--t-text-secondary)] mt-2">Cumulative multi-year business case yield.</p>
        </div>

        <div class="card p-8 bg-gradient-to-br from-[var(--t-accent)] to-[#a855f7] text-white border-none shadow-xl shadow-purple-500/20">
          <p class="text-[10px] font-black opacity-70 uppercase tracking-widest mb-2">Total Realized Value</p>
          <h2 class="text-4xl font-black">
            {{ formatCurrency(summary()?.realized_value) }}
          </h2>
          <div class="flex items-center gap-2 mt-2">
            <div class="h-1.5 flex-1 bg-white/20 rounded-full overflow-hidden">
              <div class="h-full bg-white transition-all duration-1000" [style.width.%]="getValuePercentage()"></div>
            </div>
            <span class="text-[10px] font-black">{{ getValuePercentage().toFixed(1) }}%</span>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <!-- Left: Narrative Summary -->
        <div class="xl:col-span-2 space-y-6">
          <div class="card p-8">
            <div class="flex justify-between items-center mb-6">
              <h3 class="text-sm font-black text-[var(--t-text-primary)] uppercase tracking-widest flex items-center gap-2">
                <span class="material-icons text-sm">description</span>
                Final Executive Summary
              </h3>
              @if (!isEditingSummary) {
                <button (click)="isEditingSummary = true" class="btn-ghost p-1">
                  <span class="material-icons text-sm">edit</span>
                </button>
              }
            </div>

            @if (isEditingSummary) {
              <div class="space-y-4">
                <textarea 
                  [(ngModel)]="summaryDraft"
                  rows="8"
                  class="input-field w-full text-sm leading-relaxed" 
                  placeholder="Summarize the initiative outcomes, key achievements, and final impact..."></textarea>
                <div class="flex justify-end gap-3">
                  <button (click)="isEditingSummary = false" class="btn-ghost text-xs">Cancel</button>
                  <button (click)="saveSummary()" class="btn-primary text-xs px-6">Save Summary</button>
                </div>
              </div>
            } @else {
              <p class="text-sm leading-relaxed text-[var(--t-text-secondary)] whitespace-pre-wrap">
                {{ summary()?.final_summary || 'No executive summary drafted for the final report yet.' }}
              </p>
            }
          </div>

          <div class="card p-8">
            <div class="flex justify-between items-center mb-6">
              <h3 class="text-sm font-black text-[var(--t-text-primary)] uppercase tracking-widest flex items-center gap-2">
                <span class="material-icons text-sm">emoji_objects</span>
                Lessons Learned
              </h3>
              @if (!isEditingLessons) {
                <button (click)="isEditingLessons = true" class="btn-ghost p-1">
                  <span class="material-icons text-sm">edit</span>
                </button>
              }
            </div>

            @if (isEditingLessons) {
              <div class="space-y-4">
                <textarea 
                  [(ngModel)]="lessonsDraft"
                  rows="8"
                  class="input-field w-full text-sm leading-relaxed" 
                  placeholder="What went well? What could be improved for future initiatives?"></textarea>
                <div class="flex justify-end gap-3">
                  <button (click)="isEditingLessons = false" class="btn-ghost text-xs">Cancel</button>
                  <button (click)="saveLessons()" class="btn-primary text-xs px-6">Save Lessons</button>
                </div>
              </div>
            } @else {
              <p class="text-sm leading-relaxed text-[var(--t-text-secondary)] whitespace-pre-wrap italic">
                {{ summary()?.lessons_learned || 'No lessons learned recorded for this initiative.' }}
              </p>
            }
          </div>
        </div>

        <!-- Right: Closure & Sign-off -->
        <div class="space-y-6">
          <div class="card p-8 border-t-4 border-[var(--t-green)]">
            <h3 class="text-xs font-black text-[var(--t-text-primary)] uppercase tracking-widest mb-6 flex items-center gap-2">
              <span class="material-icons text-sm text-[var(--t-green)]">verified</span>
              Closure Status
            </h3>
            
            <div class="space-y-4">
               <div class="flex items-center justify-between text-xs">
                 <span class="text-[var(--t-text-secondary)]">Stage</span>
                 <span class="font-bold text-[var(--t-text-primary)] uppercase">{{ summary()?.stage }}</span>
               </div>
               <div class="flex items-center justify-between text-xs">
                 <span class="text-[var(--t-text-secondary)]">Target Closure</span>
                 <span class="font-bold text-[var(--t-text-primary)]">{{ summary()?.completion_date | date:'MMM d, yyyy' }}</span>
               </div>
               <div class="flex items-center justify-between text-xs">
                 <span class="text-[var(--t-text-secondary)]">Approval Score</span>
                 <span class="font-bold text-[var(--t-green)]">100%</span>
               </div>
            </div>

            <div class="mt-8 pt-8 border-t border-[var(--t-border)]">
               <button class="w-full btn-primary bg-[var(--t-green)] hover:bg-green-600 border-none shadow-lg shadow-green-500/10 py-3 rounded-xl flex items-center justify-center gap-2">
                 <span class="material-icons text-sm">lock</span>
                 Finalize & Archive
               </button>
               <p class="text-[9px] text-[var(--t-text-tertiary)] text-center mt-3 uppercase font-bold tracking-widest">
                 Requires Transformation Office Sign-off
               </p>
            </div>
          </div>

          <div class="card p-6 bg-[var(--t-accent-soft)]/20 border-dashed border-[var(--t-accent)]/30">
             <div class="flex items-center gap-2 mb-3">
               <span class="material-icons text-xs text-[var(--t-accent)]">auto_awesome</span>
               <span class="text-[10px] font-black text-[var(--t-accent)] uppercase tracking-widest">AI Intelligence</span>
             </div>
             <p class="text-[11px] leading-relaxed text-[var(--t-text-primary)]">
               Transmuter detected a <span class="font-bold">12% value over-performance</span> compared to the original High Case scenario. Recommend documenting the vendor renegotiation strategy in "Lessons Learned".
             </p>
          </div>
        </div>
      </div>

    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class SummaryTabComponent implements OnInit {
  @Input() initiativeId!: string;
  
  private readonly api = inject(ApiService);
  summary = signal<any | null>(null);

  isEditingSummary = false;
  summaryDraft = '';
  
  isEditingLessons = false;
  lessonsDraft = '';

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.api.get<any>(`/initiatives/${this.initiativeId}/summary`).subscribe(res => {
      this.summary.set(res);
      this.summaryDraft = res.final_summary || '';
      this.lessonsDraft = res.lessons_learned || '';
    });
  }

  formatCurrency(val: any) {
    if (!val) return '$0.00m';
    const num = parseFloat(val);
    return `$${num.toFixed(2)}m`;
  }

  getValuePercentage() {
    const s = this.summary();
    if (!s || !s.planned_value || s.planned_value === 0) return 0;
    return (s.realized_value / s.planned_value) * 100;
  }

  saveSummary() {
    this.api.patch(`/initiatives/${this.initiativeId}/summary`, {
      final_summary: this.summaryDraft
    }).subscribe(() => {
      this.isEditingSummary = false;
      this.loadData();
    });
  }

  saveLessons() {
    this.api.patch(`/initiatives/${this.initiativeId}/summary`, {
      lessons_learned: this.lessonsDraft
    }).subscribe(() => {
      this.isEditingLessons = false;
      this.loadData();
    });
  }
}
