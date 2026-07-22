import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient, withInterceptors } from '@angular/common/http';

import { appConfig } from './app/app.config';
import { App } from './app/app';
import {
  jsonDataCacheBustingInterceptor
} from './app/core/interceptors/json-data-cache-busting.interceptor';

bootstrapApplication(App, {
  ...appConfig,
  providers: [
    ...(appConfig.providers ?? []),
    provideHttpClient(
      withInterceptors([jsonDataCacheBustingInterceptor])
    )
  ]
})
  .catch((err) => console.error(err));
