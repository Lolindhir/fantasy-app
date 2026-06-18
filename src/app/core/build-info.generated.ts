export interface AppBuildInfo {
  version: string;
  commit: string;
  shortCommit: string;
  buildDate: string;
  source: string;
}

export const APP_BUILD_INFO: AppBuildInfo = {
  version: 'local',
  commit: 'local',
  shortCommit: 'local',
  buildDate: 'local',
  source: 'repository-fallback'
};
