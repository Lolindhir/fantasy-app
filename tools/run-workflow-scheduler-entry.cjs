'use strict';

const fs = require('node:fs');
const runtime = require('./run-workflow-scheduler-runtime.cjs');
const projectFieldSync = require('./run-project-field-sync-scheduler.cjs');

const DEFAULT_STATE_READ_RETRY_DELAYS_MS = Object.freeze([1000, 2000]);
const TRANSIENT_HTTP_STATUSES = new Set([500, 502, 503, 504]);
const TRANSIENT_NETWORK_CODES = new Set([
  'ECONNRESET',
  'ECONNREFUSED',
  'EAI_AGAIN',
  'ENETUNREACH',
  'EPIPE',
  'ETIMEDOUT',
  'UND_ERR_BODY_TIMEOUT',
  'UND_ERR_CONNECT_TIMEOUT',
  'UND_ERR_HEADERS_TIMEOUT',
  'UND_ERR_SOCKET',
]);

function errorStatus(error) {
  const status = error?.status ?? error?.response?.status;
  return Number.isInteger(status) ? status : Number(status);
}

function errorCode(error) {
  return error?.code || error?.cause?.code || null;
}

function isTransientStateReadError(error) {
  const status = errorStatus(error);
  if (Number.isInteger(status) && TRANSIENT_HTTP_STATUSES.has(status)) return true;
  return TRANSIENT_NETWORK_CODES.has(errorCode(error));
}

function describeError(error) {
  const status = errorStatus(error);
  if (Number.isInteger(status)) return `HTTP ${status}`;
  const code = errorCode(error);
  if (code) return code;
  return error instanceof Error ? error.message : String(error);
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function createStateReadRetryClient({
  github,
  core,
  state,
  retryDelaysMs = DEFAULT_STATE_READ_RETRY_DELAYS_MS,
  sleepFn = sleep,
}) {
  if (!github?.rest?.repos || typeof github.rest.repos.getContent !== 'function') {
    throw new Error('GitHub client is missing repos.getContent');
  }
  if (!state?.branch || !state?.path) throw new Error('Scheduler state locator is incomplete');
  if (!Array.isArray(retryDelaysMs) || retryDelaysMs.some((value) => !Number.isInteger(value) || value < 0)) {
    throw new Error('State-read retry delays must be non-negative integer milliseconds');
  }

  const originalGetContent = github.rest.repos.getContent.bind(github.rest.repos);
  const repos = Object.create(github.rest.repos);
  repos.getContent = async (args) => {
    const isSchedulerStateRead = args?.path === state.path && args?.ref === state.branch;
    if (!isSchedulerStateRead) return originalGetContent(args);

    for (let attempt = 0; ; attempt += 1) {
      try {
        return await originalGetContent(args);
      } catch (error) {
        if (!isTransientStateReadError(error) || attempt >= retryDelaysMs.length) throw error;
        const delayMs = retryDelaysMs[attempt];
        core.warning(
          `Scheduler runtime state read failed transiently (${describeError(error)}); retrying in ${delayMs} ms `
          + `(attempt ${attempt + 2}/${retryDelaysMs.length + 1}).`,
        );
        await sleepFn(delayMs);
      }
    }
  };

  const rest = Object.create(github.rest);
  rest.repos = repos;
  const wrappedGithub = Object.create(github);
  wrappedGithub.rest = rest;
  return wrappedGithub;
}

async function run({
  github,
  context,
  core,
  configPath = '.github/workflow-schedules.json',
  now = new Date(),
  retryDelaysMs = DEFAULT_STATE_READ_RETRY_DELAYS_MS,
  sleepFn = sleep,
}) {
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const retryingGithub = createStateReadRetryClient({
    github,
    core,
    state: config.state,
    retryDelaysMs,
    sleepFn,
  });
  const results = await runtime.run({ github: retryingGithub, context, core, configPath, now });
  await projectFieldSync.run({ github, context, core, configPath, now });
  return results;
}

module.exports = {
  DEFAULT_STATE_READ_RETRY_DELAYS_MS,
  createStateReadRetryClient,
  describeError,
  errorCode,
  errorStatus,
  isTransientStateReadError,
  run,
};
