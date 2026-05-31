import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { configureSentry } from './app/core/observability/sentry';

configureSentry();
bootstrapApplication(App, appConfig)
  .catch((err) => console.error(err));
