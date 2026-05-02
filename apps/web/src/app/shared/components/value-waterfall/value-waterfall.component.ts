import { Component, Input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-value-waterfall',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card p-6">
      <div class="flex justify-between items-start mb-6">
        <h3 class="text-base font-bold" style="color:var(--t-text-primary)">
          EBITDA Value Bridge<span style="color:var(--t-accent)">.</span>
        </h3>
        @if (oneOffCost() > 0) {
          <div class="text-right">
            <span class="text-[10px] font-semibold uppercase tracking-wider text-[var(--t-text-secondary)]">One-off Costs</span>
            <p class="text-sm font-bold text-[var(--t-red)]">{{ formatMoney(-oneOffCost()) }}</p>
          </div>
        }
      </div>
      
      @if (groupedSteps().length > 0) {
        <div class="h-64 w-full flex items-end gap-4 px-2 pb-10 border-b" style="border-color:var(--t-border)">
           @for (group of groupedSteps(); track group.label) {
             <div class="relative flex-1 h-full flex items-end justify-center gap-1 group">
               
               <!-- PLANNED BAR -->
               <div class="relative w-1/2 rounded-sm transition-all opacity-80 hover:opacity-100"
                    [style.height.%]="group.p.height"
                    [style.bottom.%]="group.p.bottom"
                    style="background:#D1D5DB">
                 <div class="absolute -top-5 left-0 right-0 text-center text-[8px] font-bold text-gray-500 hidden group-hover:block z-10">
                   {{ formatMoney(group.p.value) }}
                 </div>
               </div>

               <!-- ACTUAL BAR -->
               <div class="relative w-1/2 rounded-sm transition-all opacity-90 hover:opacity-100"
                    [style.height.%]="group.a.height"
                    [style.bottom.%]="group.a.bottom"
                    [style.background]="group.a.color">
                 <div class="absolute -top-5 left-0 right-0 text-center text-[8px] font-bold hidden group-hover:block z-10"
                      [style.color]="group.a.color">
                   {{ formatMoney(group.a.value) }}
                 </div>
               </div>

               <!-- LABEL -->
               <div class="absolute -bottom-8 left-0 right-0 text-center text-[9px] font-bold uppercase tracking-tighter"
                    style="color:var(--t-text-secondary)">
                 {{ group.label }}
               </div>
             </div>
           }
        </div>

        <div class="flex items-center justify-center gap-6 mt-10">
          <span class="flex items-center gap-1.5 text-[10px] font-semibold uppercase" style="color:var(--t-text-secondary)">
            <span class="w-2.5 h-2.5 rounded-sm bg-[#D1D5DB]"></span> Planned
          </span>
          <span class="flex items-center gap-1.5 text-[10px] font-semibold uppercase" style="color:var(--t-text-secondary)">
            <span class="w-2.5 h-2.5 rounded-sm" style="background:var(--t-green)"></span> On Track / Better
          </span>
          <span class="flex items-center gap-1.5 text-[10px] font-semibold uppercase" style="color:var(--t-text-secondary)">
            <span class="w-2.5 h-2.5 rounded-sm" style="background:var(--t-amber)"></span> Slight Miss (<10%)
          </span>
          <span class="flex items-center gap-1.5 text-[10px] font-semibold uppercase" style="color:var(--t-text-secondary)">
            <span class="w-2.5 h-2.5 rounded-sm" style="background:var(--t-red)"></span> Off Track
          </span>
        </div>
      } @else {
        <div class="h-64 flex flex-col items-center justify-center text-center opacity-50">
          <span class="material-icons text-4xl mb-2">bar_chart</span>
          <p class="text-sm font-medium">No bridge data available</p>
          <p class="text-[10px]">Populate financials to see the EBITDA bridge.</p>
        </div>
      }
    </div>
  `
})
export class ValueWaterfallComponent {
  @Input() data: any = null;

  oneOffCost = computed(() => {
    if (!this.data || !this.data.base_case) return 0;
    return parseFloat(this.data.base_case.costs_one_off || '0');
  });

  groupedSteps = computed(() => {
    if (!this.data || !this.data.base_case) return [];
    
    // Planned Values
    const bc = this.data.base_case;
    const pRev = parseFloat(bc.revenue_uplift || '0');
    const pGm = parseFloat(bc.gm_uplift || '0');
    const pRecur = parseFloat(bc.costs_recurring || '0');
    const pCogs = Math.max(0, pRev - pGm);
    const pEbitda = pGm - pRecur;

    if (pRev === 0 && pGm === 0) return [];

    // Actual Values
    const ac = this.data.actual || {};
    const aRev = parseFloat(ac.revenue_uplift || '0');
    const aGm = parseFloat(ac.gm_uplift || '0');
    const aRecur = parseFloat(ac.costs_recurring || '0');
    const aCogs = Math.max(0, aRev - aGm);
    const aEbitda = aGm - aRecur;

    // --- Unified Scale Calculation (Based on Planned) ---
    const rawTotal = Math.max(pRev, 1);
    const vEbitda = Math.max(5, (pEbitda / rawTotal) * 100);
    const vRecur = Math.max(5, (pRecur / rawTotal) * 100);
    const vCogs = Math.max(5, (pCogs / rawTotal) * 100);
    
    const vTotal = vEbitda + vRecur + vCogs;

    // Helper to calculate height and bottom on this unified scale
    const calc = (val: number) => {
       const v = Math.max(0, (val / rawTotal) * 100);
       return (v / vTotal) * 100; // Normalize to 100% chart height
    };

    // Planned layout
    const hpCogs = calc(pCogs);
    const hpRecur = calc(pRecur);
    const hpEbitda = calc(pEbitda);
    
    const bpEbitda = 0;
    const hpGm = hpEbitda + hpRecur;
    const bpGm = 0;
    const bpCogs = hpGm;
    const hpRev = hpGm + hpCogs;
    const bpRev = 0;
    const bpRecur = hpEbitda;

    // Actual layout (using same scale factors)
    const haCogs = calc(aCogs);
    const haRecur = calc(aRecur);
    const haEbitda = calc(Math.max(0, aEbitda)); // Don't let height go negative
    
    const baEbitda = 0;
    const haGm = haEbitda + haRecur;
    const baGm = 0;
    const baCogs = haGm;
    const haRev = haGm + haCogs;
    const baRev = 0;
    const baRecur = haEbitda;

    const getColor = (aSigned: number, pSigned: number) => {
      if (aSigned === pSigned) return 'var(--t-green)';
      const diff = aSigned - pSigned;
      const pct = pSigned === 0 ? 0 : diff / Math.abs(pSigned);
      if (diff >= 0) return 'var(--t-green)'; // Better than plan
      if (pct >= -0.1) return 'var(--t-amber)'; // Within 10% tolerance
      return 'var(--t-red)'; // Worse
    };

    return [
      { 
        label: 'Revenue', 
        p: { value: pRev, height: hpRev, bottom: bpRev }, 
        a: { value: aRev, height: haRev, bottom: baRev, color: getColor(aRev, pRev) } 
      },
      { 
        label: 'COGS', 
        p: { value: -pCogs, height: hpCogs, bottom: bpCogs }, 
        a: { value: -aCogs, height: haCogs, bottom: baCogs, color: getColor(-aCogs, -pCogs) } 
      },
      { 
        label: 'Gross Margin', 
        p: { value: pGm, height: hpGm, bottom: bpGm }, 
        a: { value: aGm, height: haGm, bottom: baGm, color: getColor(aGm, pGm) } 
      },
      { 
        label: 'Opex', 
        p: { value: -pRecur, height: hpRecur, bottom: bpRecur }, 
        a: { value: -aRecur, height: haRecur, bottom: baRecur, color: getColor(-aRecur, -pRecur) } 
      },
      { 
        label: 'EBITDA', 
        p: { value: pEbitda, height: hpEbitda, bottom: bpEbitda }, 
        a: { value: aEbitda, height: haEbitda, bottom: baEbitda, color: getColor(aEbitda, pEbitda) } 
      },
    ];
  });

  formatMoney(val: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val);
  }
}

