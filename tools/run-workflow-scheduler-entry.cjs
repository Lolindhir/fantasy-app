'use strict';

const fs = require('node:fs');
const runtime = require('./run-workflow-scheduler-runtime.cjs');
const projectFieldSync = require('./run-project-field-sync-scheduler.cjs');
const schedulerSummary = require('./run-workflow-scheduler-summary.cjs');

const DEFAULT_STATE_READ_RETRY_DELAYS_MS = Object.freeze([1000, 2000]);
const scheduler = require('./run-workflow-scheduler.cjs');

const DEFAULT_API_READ_RETRY_DELAYS_MS = Object.freeze([2000, 5000, 10000]);
const MAX_RETRY_AFTER_MS = 30000;
const JITTER_MAX_MS = 1000;

function errorStatus(error) {
  const status = error?.status ?? error?.response?.status;
  return Number.isInteger(status) ? status : Number(status);
}

function errorCode(error) {
  return error?.code || error?.cause?.code || null;
}

function isTransientStateReadError(error) {
  return scheduler.isTransientApiError(error);
}

function retryAfterMs(error) {
  const header = error?.response?.headers?.['retry-after'] ?? error?.headers?.['retry-after'];
  const seconds = Number(header);
  if (!Number.isFinite(seconds) || seconds <= 0) return 0;
  return Math.min(seconds * 1000, MAX_RETRY_AFTER_MS);
}

function defaultJitterMs() {
  return Math.floor(Math.random() * JITTER_MAX_MS);
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
  apiRetryDelaysMs = DEFAULT_API_READ_RETRY_DELAYS_MS,
  jitterFn = defaultJitterMs,
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

  // Workflow-run list reads are idempotent: retry transient failures (5xx, 429, network) with backoff and jitter.
  // Dispatch events are deliberately not wrapped because a 5xx leaves it unknown whether the event was delivered.
  if (typeof github.rest.actions?.listWorkflowRuns === 'function') {
    if (!Array.isArray(apiRetryDelaysMs) || apiRetryDelaysMs.some((value) => !Number.isInteger(value) || value < 0)) {
      throw new Error('API-read retry delays must be non-negative integer milliseconds');
    }
    const originalList = github.rest.actions.listWorkflowRuns.bind(github.rest.actions);
    const actions = Object.create(github.rest.actions);
    actions.listWorkflowRuns = async (args) => {
      for (let attempt = 0; ; attempt += 1) {
        try {
          return await originalList(args);
        } catch (error) {
          if (!isTransientStateReadError(error) || attempt >= apiRetryDelaysMs.length) throw error;
          const delayMs = Math.max(apiRetryDelaysMs[attempt], retryAfterMs(error)) + jitterFn();
          core.warning(
            `listWorkflowRuns for ${args?.workflow_id || 'unknown workflow'}${args?.event ? ` (event ${args.event})` : ''} failed transiently `
            + `(${describeError(error)}); retrying in ${delayMs} ms (attempt ${attempt + 2}/${apiRetryDelaysMs.length + 1}).`,
          );
          await sleepFn(delayMs);
        }
      }
    };
    rest.actions = actions;
  }
  const wrappedGithub = Object.create(github);
  wrappedGithub.rest = rest;
  return wrappedGithub;
}

async function writeCombinedSummarySafely({ core, results, projectFieldResult, now, config }) {
  try {
    await schedulerSummary.writeCombinedSummary(core, results, projectFieldResult, now, config);
  } catch (error) {
    core.warning(`Could not write combined scheduler summary: ${describeError(error)}`);
  }
}

async function run({
  github,
  context,
  core,
  configPath = '.github/workflow-schedules.json',
  now = new Date(),
  retryDelaysMs = DEFAULT_STATE_READ_RETRY_DELAYS_MS,
  apiRetryDelaysMs = DEFAULT_API_READ_RETRY_DELAYS_MS,
  jitterFn = defaultJitterMs,
  sleepFn = sleep,
}) {
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const retryingGithub = createStateReadRetryClient({
    github,
    core,
    state: config.state,
    retryDelaysMs,
    apiRetryDelaysMs,
    jitterFn,
    sleepFn,
  });
  const results = await runtime.run({
    github: retryingGithub, context, core, configPath, now, stateReadRetryDelaysMs: retryDelaysMs, sleepFn,
  });

  let projectFieldResult;
  try {
    projectFieldResult = await projectFieldSync.run({ github: retryingGithub, context, core, configPath, now });
  } catch (error) {
    projectFieldResult = {
      id: 'project-fields',
      workflow: config.projectFieldSync?.workflow || null,
      decision: 'error',
      error: describeError(error),
      issueNumbers: [],
    };
    await writeCombinedSummarySafely({ core, results, projectFieldResult, now, config });
    throw error;
  }

  // runtime.run() writes the normal target summary before Project-field evaluation.
  // Overwrite that intermediate view only after every scheduler-integrated decision is known,
  // otherwise late decision paths can work correctly while remaining invisible to operators.
  await writeCombinedSummarySafely({ core, results, projectFieldResult, now, config });
  return [...results, projectFieldResult];
}

module.exports = {
  DEFAULT_API_READ_RETRY_DELAYS_MS,
  DEFAULT_STATE_READ_RETRY_DELAYS_MS,
  createStateReadRetryClient,
  describeError,
  errorCode,
  errorStatus,
  isTransientStateReadError,
  run,
  writeCombinedSummarySafely,
};
