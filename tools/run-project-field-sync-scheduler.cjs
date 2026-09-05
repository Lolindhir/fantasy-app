'use strict';

const fs = require('node:fs');

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

function evaluateProjectFieldSync({ now, since, issues, inFlight, config }) {
  const sync = validateProjectFieldSyncConfig({ projectFieldSync: config });
  const sinceMs = Date.parse(since || '');
  if (!Number.isFinite(sinceMs)) throw new Error(`Invalid Project field sync watermark: ${since}`);

  if (inFlight) {
    return {
      decision: 'in-flight',
      since,
      inFlightRunId: inFlight.id,
      inFlightCreatedAt: inFlight.created_at || null,
      issueNumbers: [],
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
    return { decision: 'idle', since, issueNumbers: [] };
  }

  const byNumber = new Map();
  for (const issue of changed) {
    const current = byNumber.get(issue.number);
    if (!current || issue.updatedAtMs > current.updatedAtMs) byNumber.set(issue.number, issue);
  }
  const unique = [...byNumber.values()];
  const firstPending = unique.reduce((left, right) => (left.updatedAtMs <= right.updatedAtMs ? left : right));
  const latestPending = unique.reduce((left, right) => (left.updatedAtMs >= right.updatedAtMs ? left : right));
  const quietAgeMinutes = Math.max(0, Math.floor((now.getTime() - latestPending.updatedAtMs) / 60000));
  const pendingAgeMinutes = Math.max(0, Math.floor((now.getTime() - firstPending.updatedAtMs) / 60000));
  const quietReached = now.getTime() - latestPending.updatedAtMs >= sync.quietMinutes * 60000;
  const maxWaitReached = now.getTime() - firstPending.updatedAtMs >= sync.maxWaitMinutes * 60000;
  const issueNumbers = unique.map((issue) => issue.number).sort((left, right) => left - right);
  const common = {
    since,
    firstPendingAt: firstPending.updatedAt,
    latestUpdateAt: latestPending.updatedAt,
    quietAgeMinutes,
    pendingAgeMinutes,
    issueNumbers,
  };

  if (!quietReached && !maxWaitReached) {
    return { ...common, decision: 'debounce' };
  }
  return {
    ...common,
    decision: 'dispatch',
    dispatchReason: maxWaitReached ? 'max-wait-reached' : 'quiet-period-met',
  };
}

async function run({ github, context, core, configPath = '.github/workflow-schedules.json', now = new Date() }) {
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const sync = validateProjectFieldSyncConfig(config);
  if (config.repository !== `${context.repo.owner}/${context.repo.repo}`) {
    throw new Error(`Project field sync repository mismatch: config=${config.repository} runtime=${context.repo.owner}/${context.repo.repo}`);
  }

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

  const result = evaluateProjectFieldSync({ now, since, issues, inFlight, config: sync });
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
        first_pending_at: result.firstPendingAt,
        latest_update_at: result.latestUpdateAt,
        reason: result.dispatchReason,
        issue_numbers: result.issueNumbers,
      },
    });
    logged.dispatched = true;
  }

  core.info(JSON.stringify(logged));
  return logged;
}

module.exports = {
  evaluateProjectFieldSync,
  run,
  selectInFlightBatchRun,
  selectWatermarkRun,
  validateProjectFieldSyncConfig,
};
