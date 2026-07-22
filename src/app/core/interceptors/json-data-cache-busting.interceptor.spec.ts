import {
  HttpHandlerFn,
  HttpRequest,
  HttpResponse
} from '@angular/common/http';
import { of } from 'rxjs';

import { APP_BUILD_INFO } from '../build-info.generated';
import { jsonDataCacheBustingInterceptor } from './json-data-cache-busting.interceptor';

describe('jsonDataCacheBustingInterceptor', () => {
  it('adds the build commit to a JSON file in the data root', () => {
    expect(intercept('data/Drafts.json').urlWithParams).toBe(
      `data/Drafts.json?build=${APP_BUILD_INFO.commit}`
    );
  });

  it('adds the build commit to future nested JSON files under data', () => {
    expect(intercept('data/current/Statistics.json').urlWithParams).toBe(
      `data/current/Statistics.json?build=${APP_BUILD_INFO.commit}`
    );
  });

  it('keeps PastSeasonsIndex versioned because it is outside past_seasons', () => {
    expect(intercept('data/PastSeasonsIndex.json').urlWithParams).toBe(
      `data/PastSeasonsIndex.json?build=${APP_BUILD_INFO.commit}`
    );
  });

  it('does not version historical files under data/past_seasons', () => {
    expect(intercept('data/past_seasons/Drafts/Drafts_2025.json').urlWithParams).toBe(
      'data/past_seasons/Drafts/Drafts_2025.json'
    );
  });

  it('preserves existing query parameters', () => {
    expect(intercept('data/Drafts.json?language=en').urlWithParams).toBe(
      `data/Drafts.json?language=en&build=${APP_BUILD_INFO.commit}`
    );
  });

  it('does not change non-JSON files', () => {
    expect(intercept('data/team-logo.png').urlWithParams).toBe('data/team-logo.png');
  });

  it('does not change JSON requests outside the app data directory', () => {
    expect(intercept('assets/example.json').urlWithParams).toBe('assets/example.json');
  });

  it('does not change external JSON requests', () => {
    expect(intercept('https://example.com/data/example.json').urlWithParams).toBe(
      'https://example.com/data/example.json'
    );
  });

  it('does not change non-GET requests', () => {
    expect(intercept('data/Drafts.json', 'POST').urlWithParams).toBe('data/Drafts.json');
  });
});

function intercept(url: string, method = 'GET'): HttpRequest<unknown> {
  let handledRequest: HttpRequest<unknown> | undefined;

  const next: HttpHandlerFn = request => {
    handledRequest = request;
    return of(new HttpResponse({ status: 200 }));
  };

  jsonDataCacheBustingInterceptor(
    new HttpRequest(method, url),
    next
  ).subscribe();

  if (handledRequest === undefined) {
    throw new Error('The interceptor did not forward the request.');
  }

  return handledRequest;
}
