import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiService } from '../../../core/services/api.service';
import { GetStartedComponent } from './get-started.component';

describe('GetStartedComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GetStartedComponent],
      providers: [
        provideRouter([]),
        {
          provide: ApiService,
          useValue: {
            post: vi.fn(() => of({ checkout_url: 'https://stripe.example/checkout' })),
          },
        },
      ],
    }).compileComponents();
  });

  it('should format backend validation errors into readable messages', () => {
    const fixture = TestBed.createComponent(GetStartedComponent);
    const component = fixture.componentInstance as any;

    expect(
      component.formatCheckoutError({
        error: {
          detail: [
            { loc: ['body', 'organization_slug'], msg: 'String should match pattern', type: 'string_pattern_mismatch' },
          ],
        },
      })
    ).toBe('String should match pattern');

    expect(component.formatCheckoutError({ error: { detail: { message: 'slug too short' } } })).toBe('slug too short');
    expect(component.formatCheckoutError({ error: { detail: 'Could not start checkout' } })).toBe('Could not start checkout');
  });
});
