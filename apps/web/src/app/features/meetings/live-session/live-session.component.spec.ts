import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { TenantReportingContextService } from '../../../core/services/tenant-reporting-context.service';
import { TimezoneOptionsService } from '../../../core/services/timezone-options.service';
import { LiveSessionComponent } from './live-session.component';

describe('LiveSessionComponent Microsoft transcript sync', () => {
  function configure(syncResponse: object) {
    const post = vi.fn(() => of(syncResponse));
    TestBed.configureTestingModule({
      imports: [LiveSessionComponent],
      providers: [
        { provide: ApiService, useValue: { get: vi.fn(() => of({ data: [], items: [] })), patch: vi.fn(() => of({})), post } },
        { provide: AuthService, useValue: { hasPermission: vi.fn(() => true) } },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => null } } } },
        { provide: Router, useValue: { navigate: vi.fn() } },
        {
          provide: TimezoneOptionsService,
          useValue: {
            browserTimezone: () => 'UTC',
            load: vi.fn(),
            optionsWithCurrent: () => [{ value: 'UTC', label: 'UTC' }],
          },
        },
        {
          provide: TenantReportingContextService,
          useValue: { ensureLoaded: vi.fn(), formatMoney: () => '$0' },
        },
      ],
    });
    const fixture = TestBed.createComponent(LiveSessionComponent);
    fixture.componentInstance.session.set({
      id: 'session-1',
      meeting_id: 'meeting-1',
      status: 'completed',
      agenda: [],
      artifacts: [],
      attendees: [],
      meetings: { name: 'Transmuter Daily' },
    });
    fixture.detectChanges();
    fixture.componentInstance.openTranscriptModal();
    return { fixture, post };
  }

  it('renders unavailable Microsoft details inside the open transcript modal', () => {
    const { fixture } = configure({
      status: 'unavailable',
      detail: 'Microsoft Graph reconnection is required.',
      session: null,
    });

    fixture.componentInstance.syncMicrosoftTranscript();
    fixture.detectChanges();

    expect(fixture.componentInstance.showTranscriptImport()).toBe(true);
    expect(fixture.nativeElement.querySelector('[data-testid="transcript-sync-error"]')?.textContent)
      .toContain('Microsoft Graph reconnection is required.');
  });

  it('keeps successful Microsoft transcript text visible in the modal', async () => {
    const { fixture } = configure({
      status: 'synced',
      session: { id: 'session-1', transcript_text: 'Speaker: Approved the plan' },
    });

    fixture.componentInstance.syncMicrosoftTranscript();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.showTranscriptImport()).toBe(true);
    expect(fixture.componentInstance.transcriptDraft).toBe('Speaker: Approved the plan');
    expect(fixture.nativeElement.querySelector('textarea[aria-label="Transcript text"]')?.value)
      .toBe('Speaker: Approved the plan');
    expect(fixture.nativeElement.querySelector('[data-testid="transcript-sync-message"]')?.textContent)
      .toContain('Microsoft Teams transcript synced.');
  });
});
