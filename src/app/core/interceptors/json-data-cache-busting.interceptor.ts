import { HttpInterceptorFn } from '@angular/common/http';

import { APP_BUILD_INFO } from '../build-info.generated';

const BUILD_QUERY_PARAMETER = 'build';
const DATA_DIRECTORY = 'data/';
const HISTORICAL_DATA_DIRECTORY = 'past_seasons/';

export const jsonDataCacheBustingInterceptor: HttpInterceptorFn = (request, next) => {
  if (!shouldVersionDataRequest(request.method, request.url)) {
    return next(request);
  }

  return next(request.clone({
    params: request.params.set(BUILD_QUERY_PARAMETER, APP_BUILD_INFO.commit)
  }));
};

export function shouldVersionDataRequest(method: string, requestUrl: string): boolean {
  if (method.toUpperCase() !== 'GET') {
    return false;
  }

  const dataRelativePath = getLocalDataRelativePath(requestUrl);

  if (dataRelativePath === null) {
    return false;
  }

  const normalizedDataPath = dataRelativePath.toLowerCase();

  return normalizedDataPath.endsWith('.json')
    && !normalizedDataPath.startsWith(HISTORICAL_DATA_DIRECTORY);
}

function getLocalDataRelativePath(requestUrl: string): string | null {
  try {
    const appBaseUrl = new URL(document.baseURI);
    const requestAbsoluteUrl = new URL(requestUrl, appBaseUrl);

    if (requestAbsoluteUrl.origin !== appBaseUrl.origin) {
      return null;
    }

    const normalizedBasePath = ensureTrailingSlash(appBaseUrl.pathname);
    const dataRootPath = `${normalizedBasePath}${DATA_DIRECTORY}`.replace(/\/{2,}/g, '/');
    const normalizedRequestPath = requestAbsoluteUrl.pathname.replace(/\/{2,}/g, '/');

    if (!normalizedRequestPath.startsWith(dataRootPath)) {
      return null;
    }

    return normalizedRequestPath.slice(dataRootPath.length);
  } catch {
    return null;
  }
}

function ensureTrailingSlash(path: string): string {
  return path.endsWith('/') ? path : `${path}/`;
}
