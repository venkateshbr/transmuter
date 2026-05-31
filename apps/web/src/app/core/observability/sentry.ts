import { ErrorHandler, inject, provideAppInitializer } from '@angular/core';
import { TraceService, browserTracingIntegration, createErrorHandler, init } from '@sentry/angular';
import { environment } from '../../../environments/environment';

declare global {
  interface Window {
    __TRANSMUTER_SENTRY_DSN__?: string;
    __TRANSMUTER_ENVIRONMENT__?: string;
  }
}

export function configureSentry(): void {
  const dsn = window.__TRANSMUTER_SENTRY_DSN__ || environment.sentryDsn;
  if (!dsn) return;

  init({
    dsn,
    environment: window.__TRANSMUTER_ENVIRONMENT__ || environment.sentryEnvironment,
    release: 'transmuter-web',
    integrations: [browserTracingIntegration()],
    tracesSampleRate: environment.sentryTracesSampleRate,
    sendDefaultPii: false,
    beforeSend(event) {
      if (event.user) {
        delete event.user.email;
        delete event.user['name'];
      }
      return event;
    },
  });
}

export const sentryProviders = [
  {
    provide: ErrorHandler,
    useValue: createErrorHandler({ logErrors: !environment.production }),
  },
  provideAppInitializer(() => {
    inject(TraceService);
  }),
];
