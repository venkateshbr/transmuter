import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { describe, expect, it } from 'vitest';
import { OperationsHubComponent } from './operations-hub.component';

describe('OperationsHubComponent', () => {
  it('shows only the selected operating discipline', async () => {
    await TestBed.configureTestingModule({
      imports: [OperationsHubComponent],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { data: { section: 'financial' } } } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(OperationsHubComponent);
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent || '';

    expect(text).toContain('Financial Operations');
    expect(text).toContain('Benefit Ledger');
    expect(text).not.toContain('Initiative Pipeline');
    expect(text).not.toContain('Gate Approvals');
    expect(text).not.toContain('Benefit Validation');
  });
});
