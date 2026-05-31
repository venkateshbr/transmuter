import { HttpContextToken, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { finalize } from 'rxjs';
import { LoadingService } from '../services/loading.service';

export const SKIP_BLOCKING_LOADER = new HttpContextToken<boolean>(() => false);

const BACKGROUND_PATHS = ['/ai/chat', '/auth/login'];

export const loadingInterceptor: HttpInterceptorFn = (req, next) => {
  const loading = inject(LoadingService);
  const shouldTrack = req.method === 'GET'
    && !req.context.get(SKIP_BLOCKING_LOADER)
    && !BACKGROUND_PATHS.some(path => req.url.includes(path));

  if (!shouldTrack) return next(req);

  loading.beginRequest();
  return next(req).pipe(finalize(() => loading.endRequest()));
};
