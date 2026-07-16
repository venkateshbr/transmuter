import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, throwError } from 'rxjs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { PipelineComponent } from './pipeline.component';

describe('PipelineComponent CSV export', () => {
  let fixture: ComponentFixture<PipelineComponent>;
  let getBlob: ReturnType<typeof vi.fn>;
  let anchorClick: ReturnType<typeof vi.spyOn>;

  beforeEach(async () => {
    getBlob = vi.fn(() => of(new Blob(['initiative_code,name\nENT-001,Demo\n'], { type: 'text/csv' })));
    const get = vi.fn((path: string) => {
      if (path === '/dashboard') return of({ available_filters: {} });
      if (path === '/governance/stage-gates') return of([]);
      return of({ items: [], total: 0 });
    });
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: vi.fn(() => 'blob:initiative-export'),
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: vi.fn(),
    });
    anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);

    await TestBed.configureTestingModule({
      imports: [PipelineComponent],
      providers: [
        { provide: ApiService, useValue: { get, getBlob, post: vi.fn() } },
        { provide: AuthService, useValue: { hasPermission: vi.fn(() => true) } },
        { provide: ActivatedRoute, useValue: { queryParamMap: of(convertToParamMap({})) } },
        { provide: Router, useValue: { navigate: vi.fn(() => Promise.resolve(false)) } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PipelineComponent);
    fixture.detectChanges();
  });

  afterEach(() => anchorClick.mockRestore());

  it('downloads CSV through the authenticated API service', () => {
    fixture.componentInstance.exportCsv();

    expect(getBlob).toHaveBeenCalledWith('/initiatives/export');
    expect(anchorClick).toHaveBeenCalledOnce();
    expect(fixture.componentInstance.exportingCsv()).toBe(false);
    expect(fixture.componentInstance.exportError()).toBeNull();
  });

  it('shows a bounded error when export fails', () => {
    getBlob.mockReturnValueOnce(throwError(() => new Error('network')));

    fixture.componentInstance.exportCsv();
    fixture.detectChanges();

    expect(fixture.componentInstance.exportError()).toBe('Initiative CSV export failed. Try again.');
    expect(fixture.nativeElement.querySelector('[role="alert"]')?.textContent).toContain('Initiative CSV export failed. Try again.');
  });
});
