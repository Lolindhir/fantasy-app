'use strict';

const fs = require('node:fs');
const schedulerState = require('./run-workflow-scheduler.cjs');

function validateProjectFieldSyncConfig(config) {
  const sync = config?.projectFieldSync;
  if (!sync || typeof sync !== 'object' || Array.isArray(sync)) {
    throw new Error('Missing projectFieldSync scheduler config');
  }
  for (const key of ['workflow', 'eventType']) {
    if (typeof sync[key] !== 'string' || sync[key].trim() === '') {
      throw new Error(`Invalid projectFieldSync ${key}`);
    }
  }
  for (const key of ['quietMinutes', 'maxWaitMinutes', 'bootstrapLookbackMinutes']) {
    if (!Number.isInteger(sync[key]) || sync[key] <= 0) {
      throw new Error(`Invalid projectFieldSync ${key}`);
    }
  }
  if (sync.maxWaitMinutes < sync.quietMinutes) {
    throw new Error('projectFieldSync maxWaitMinutes must be >= quietMinutes');
  }
  return sync;
}

function newestRun(runs) {
  return [...runs].sort((left, right) => Date.parse(right.created_at || '') - Date.parse(left.created_at || ''))[0] || null;
}

function selectWatermarkRun(runs) {
  const successful = (runs || []).filter((run) => run.status === 'completed' && run.conclusion === 'success');
  const batch = newestRun(successful.filter((run) => run.event === 'repository_dispatch'));
  if (batch) return batch;
  return newestRun(successful.filter((run) => run.event === 'issues'));
}

function selectInFlightBatchRun(runs) {
  return newestRun((runs || []).filter((run) => run.event === 'repository_dispatch' && run.status && run.status !== 'completed'));
}

function parsePendingState(pendingState) {
  if (pendingState === null || pendingState === undefined) return null;
  if (!pendingState || typeof pendingState !== 'object' || Array.isArray(pendingState)) {
    throw new Error('Invalid Project field sync pending state');
  }
  const pendingSinceMs = Date.parse(pendingState.pendingSince || '');
  if (!Number.isFinite(pendingSinceMs)) throw new Error('Invalid Project field sync pendingSince');
  return { pendingSince: new Date(pendingSinceMs).toISOString(), pendingSinceMs };
}

function evaluateProjectFieldSync({ now, since, issues, inFlight, config, pendingState = null }) {
  const sync = validateProjectFieldSyncConfig({ projectFieldSync: config });
  const sinceMs = Date.parse(since || '');
  if (!Number.isFinite(sinceMs)) throw new Error(`Invalid Project field sync watermark: ${since}`);
  const persistedPending = parsePendingState(pendingState);

  if (inFlight) {
    return {
      result: {
        decision: 'in-flight',
        since,
        inFlightRunId: inFlight.id,
        inFlightCreatedAt: inFlight.created_at || null,
        issueNumbers: [],
      },
      nextState: null,
    };
  }

  const changed = (issues || [])
    .filter((issue) => !issue.pull_request)
    .map((issue) => ({
      number: Number(issue.number),
      updatedAt: issue.updated_at,
      updatedAtMs: Date.parse(issue.updated_at || ''),
    }))
    .filter((issue) => Number.isInteger(issue.number) && issue.number > 0 && Number.isFinite(issue.updatedAtMs) && issue.updatedAtMs > sinceMs);

  if (changed.length === 0) {
    return { result: { decision: 'idle', since, issueNumbers: [] }, nextState: null };
  }

  const byNumber = new Map();
  for (const issue of changed) {
    const current = byNumber.get(issue.number);
    if (!current || issue.updatedAtMs > current.updatedAtMs) byNumber.set(issue.number, issue);
  }
  const unique = [...byNumber.values()];
  const earliestCurrent = unique.reduce((left, right) => (left.updatedAtMs <= right.updatedAtMs ? left : right));
  const latestPending = unique.reduce((left, right) => (left.updatedAtMs >= right.updatedAtMs ? left : right));
  const pendingSinceMs = persistedPending?.pendingSinceMs ?? earliestCurrent.updatedAtMs;
  const pendingSince = new Date(pendingSinceMs).toISOString();
  const quietAgeMinutes = Math.max(0, Math.floor((now.getTime() - latestPending.updatedAtMs) / 60000));
  const pendingAgeMinutes = Math.max(0, Math.floor((now.getTime() - pendingSinceMs) / 60000));
  const quietReached = now.getTime() - latestPending.updatedAtMs >= sync.quietMinutes * 60000;
  const maxWaitReached = now.getTime() - pendingSinceMs >= sync.maxWaitMinutes * 60000;
  const issueNumbers = unique.map((issue) => issue.number).sort((left, right) => left - right);
  const common = {
    since,
    pendingSince,
    latestUpdateAt: latestPending.updatedAt,
    quietAgeMinutes,
    pendingAgeMinutes,
    issueNumbers,
  };

  if (!quietReached && !maxWaitReached) {
    return {
      result: { ...common, decision: 'debounce' },
      nextState: { pendingSince },
    };
  }
  return {
    result: {
      ...common,
      decision: 'dispatch',
      dispatchReason: maxWaitReached ? 'max-wait-reached' : 'quiet-period-met',
    },
    nextState: null,
  };
}

async function run({ github, context, core, configPath = '.github/workflow-schedules.json', now = new Date() }) {
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const sync = validateProjectFieldSyncConfig(config);
  if (config.repository !== `${context.repo.owner}/${context.repo.repo}`) {
    throw new Error(`Project field sync repository mismatch: config=${config.repository} runtime=${context.repo.owner}/${context.repo.repo}`);
  }

  const loadedState = await schedulerState.loadSchedulerState({ github, context, config, core });
  const runtimeState = JSON.parse(JSON.stringify(loadedState.state));

  const runsResponse = await github.rest.actions.listWorkflowRuns({
    owner: context.repo.owner,
    repo: context.repo.repo,
    workflow_id: sync.workflow,
    per_page: 100,
  });
  const runs = runsResponse.data.workflow_runs || [];
  const watermarkRun = selectWatermarkRun(runs);
  const since = watermarkRun?.created_at
    || new Date(now.getTime() - sync.bootstrapLookbackMinutes * 60000).toISOString();
  const inFlight = selectInFlightBatchRun(runs);

  const issueArgs = {
    owner: context.repo.owner,
    repo: context.repo.repo,
    state: 'all',
    sort: 'updated',
    direction: 'asc',
    since,
    per_page: 100,
  };
  const issues = typeof github.paginate === 'function'
    ? await github.paginate(github.rest.issues.listForRepo, issueArgs)
    : (await github.rest.issues.listForRepo(issueArgs)).data;

  const evaluation = evaluateProjectFieldSync({
    now,
    since,
    issues,
    inFlight,
    config: sync,
    pendingState: runtimeState.projectFieldSync || null,
  });
  const result = evaluation.result;
  const logged = { id: 'project-fields', workflow: sync.workflow, ...result };

  if (result.decision === 'dispatch') {
    await github.rest.repos.createDispatchEvent({
      owner: context.repo.owner,
      repo: context.repo.repo,
      event_type: sync.eventType,
      client_payload: {
        scheduler_id: 'project-fields',
        workflow: sync.workflow,
        requested_at: now.toISOString(),
        since: result.since,
        pending_since: result.pendingSince,
        latest_update_at: result.latestUpdateAt,
        reason: result.dispatchReason,
        issue_numbers: result.issueNumbers,
      },
    });
    logged.dispatched = true;
  }

  if (evaluation.nextState) runtimeState.projectFieldSync = evaluation.nextState;
  else delete runtimeState.projectFieldSync;

  await schedulerState.persistSchedulerState({
    github,
    context,
    config,
    core,
    state: runtimeState,
    previousSerialized: loadedState.serialized,
    existed: loadedState.exists,
  });

  core.info(JSON.stringify(logged));
  return logged;
}

module.exports = {
  evaluateProjectFieldSync,
  parsePendingState,
  run,
  selectInFlightBatchRun,
  selectWatermarkRun,
  validateProjectFieldSyncConfig,
};
