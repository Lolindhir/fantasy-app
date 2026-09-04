'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const scheduler = require('../run-workflow-scheduler-runtime.cjs');

function target(overrides = {}) {
  return {
    id: 'league',
    workflow: 'update-league.yml',
    eventType: 'scheduler-update-league',
    profile: 'productive',
    timezone: 'Etc/UTC',
    cron: ['*/10 * * * *'],
    satisfyingEvents: ['repository_dispatch', 'schedule', 'workflow_dispatch'],
    ...overrides,
  };
}

const productive = { healthBarrier: true, retryPolicy: 'standard' };
const retryPolicy = {
  maxAttempts: 3,
  backoffMinutes: [5, 10],
  cooldownMinutes: 60,
  dispatchObservationTimeoutMinutes: 15,
};

function run(id, createdAt, status, conclusion, extra = {}) {
  return {
    id,
    event: 'repository_dispatch',
    head_branch: 'main',
    created_at: createdAt,
    updated_at: extra.updated_at || createdAt,
    status,
    conclusion,
    ...extra,
  };
}

test('persisted dispatch with temporarily empty run history awaits observation instead of retrying', () => {
  const evaluation = scheduler.evaluateTargetWithRetry(
    target(), productive, retryPolicy, 'main', new Date('2026-09-04T13:39:00Z'), 180, [],
    {
      dueAt: '2026-09-04T13:30:00.000Z',
      attemptsDispatched: 1,
      lastDispatchAt: '2026-09-04T13:32:55.000Z',
      lastFailureRunId: null,
      lastFailureConclusion: null,
    },
  );
  assert.equal(evaluation.result.decision, 'awaiting-observation');
  assert.equal(evaluation.result.attemptsDispatched, 1);
  assert.equal(evaluation.result.observedAttempts, 0);
  assert.equal(evaluation.result.unobservedDispatches, 1);
  assert.equal(evaluation.result.retryAttempt, undefined);
  assert.equal(evaluation.nextState.attemptsDispatched, 1);
});

test('missing newest dispatch does not let an older observed failure advance the retry cycle', () => {
  const evaluation = scheduler.evaluateTargetWithRetry(
    target(), productive, retryPolicy, 'main', new Date('2026-09-04T13:39:00Z'), 180,
    [run(501, '2026-09-04T13:31:00Z', 'completed', 'failure', { updated_at: '2026-09-04T13:32:00Z' })],
    {
      dueAt: '2026-09-04T13:30:00.000Z',
      attemptsDispatched: 2,
      lastDispatchAt: '2026-09-04T13:36:00.000Z',
      lastFailureRunId: 501,
      lastFailureConclusion: 'failure',
    },
  );
  assert.equal(evaluation.result.decision, 'awaiting-observation');
  assert.equal(evaluation.result.attemptsDispatched, 2);
  assert.equal(evaluation.result.observedAttempts, 1);
  assert.equal(evaluation.result.unobservedDispatches, 1);
  assert.equal(evaluation.result.retryAttempt, undefined);
});

test('observation timeout opens a circuit instead of starting a blind retry', () => {
  const evaluation = scheduler.evaluateTargetWithRetry(
    target(), productive, retryPolicy, 'main', new Date('2026-09-04T13:50:00Z'), 180, [],
    {
      dueAt: '2026-09-04T13:30:00.000Z',
      attemptsDispatched: 1,
      lastDispatchAt: '2026-09-04T13:32:00.000Z',
    },
  );
  assert.equal(evaluation.result.decision, 'observation-timeout');
  assert.equal(evaluation.result.circuitOpenUntil, '2026-09-04T14:47:00.000Z');
  assert.equal(evaluation.nextState.circuitReason, 'dispatch-observation-timeout');
  assert.equal(evaluation.result.retryAttempt, undefined);
});

test('observation cooldown suppresses dispatches and later allows a fresh current-slot probe', () => {
  const state = {
    dueAt: '2026-09-04T13:30:00.000Z',
    attemptsDispatched: 1,
    lastDispatchAt: '2026-09-04T13:32:00.000Z',
    circuitOpenUntil: '2026-09-04T14:47:00.000Z',
    circuitReason: 'dispatch-observation-timeout',
  };
  const cooling = scheduler.evaluateTargetWithRetry(
    target(), productive, retryPolicy, 'main', new Date('2026-09-04T14:00:00Z'), 180, [], state,
  );
  assert.equal(cooling.result.decision, 'observation-cooldown');

  const after = scheduler.evaluateTargetWithRetry(
    target(), productive, retryPolicy, 'main', new Date('2026-09-04T14:50:00Z'), 180, [], state,
  );
  assert.equal(after.result.decision, 'dispatch');
  assert.equal(after.result.dueAt, '2026-09-04T14:50:00.000Z');
  assert.equal(after.result.retryAttempt, 1);
});

test('fallback workflow-run query recovers a success omitted by the branch-filtered query', async () => {
  const calls = [];
  const success = run(33878678558, '2026-09-04T13:32:56Z', 'completed', 'success', { updated_at: '2026-09-04T13:34:55Z' });
  const github = {
    rest: {
      actions: {
        listWorkflowRuns: async (args) => {
          calls.push(args);
          if (args.branch) return { data: { workflow_runs: [] } };
          return { data: { workflow_runs: [success] } };
        },
      },
    },
  };
  const evaluation = await scheduler.evaluateTargetFromGithub({
    github,
    context: { repo: { owner: 'Lolindhir', repo: 'fantasy-app' } },
    target: target(),
    profile: productive,
    retryPolicy,
    ref: 'main',
    now: new Date('2026-09-04T13:39:00Z'),
    lookbackMinutes: 180,
    targetState: {
      dueAt: '2026-09-04T13:30:00.000Z',
      attemptsDispatched: 1,
      lastDispatchAt: '2026-09-04T13:32:55.000Z',
    },
  });
  assert.equal(evaluation.result.decision, 'satisfied');
  assert.equal(evaluation.result.satisfyingRunId, 33878678558);
  assert.equal(evaluation.result.runQueryFallbackUsed, true);
  assert.equal(evaluation.result.runQueryFallbackRecovered, true);
  assert.equal(calls.length, 2);
  assert.equal(calls[0].branch, 'main');
  assert.equal(calls[1].branch, undefined);
  assert.equal(calls[1].event, 'repository_dispatch');
});

test('awaiting observation uses its own dispatch time for the Health anti-starvation window', () => {
  const healthTarget = target({
    id: 'workflow-health',
    workflow: 'workflow-health-snapshot.yml',
    eventType: 'scheduler-workflow-health',
    profile: 'observer',
    deferUntilOtherTargetsSettled: { maxMinutes: 20 },
  });
  const healthResult = {
    id: 'workflow-health', workflow: 'workflow-health-snapshot.yml', profile: 'observer', healthBarrier: false,
    decision: 'dispatch', dueAt: '2026-09-04T10:37:00.000Z',
  };
  const peer = {
    id: 'league', workflow: 'update-league.yml', profile: 'productive', healthBarrier: true,
    decision: 'awaiting-observation', dueAt: '2026-09-04T13:30:00.000Z', lastDispatchAt: '2026-09-04T17:22:00.000Z',
  };
  const before = scheduler.applyTargetDeferral(healthTarget, healthResult, [healthResult, peer], new Date('2026-09-04T17:25:00Z'));
  assert.equal(before.decision, 'deferred');
  assert.equal(before.deferralReason, 'productive-in-flight-or-unobserved');
  assert.equal(before.deferralAgeAnchor, 'productive-blocker-start');
  assert.equal(before.deferralAgeMinutes, 3);

  const after = scheduler.applyTargetDeferral(healthTarget, healthResult, [healthResult, peer], new Date('2026-09-04T17:43:00Z'));
  assert.equal(after.decision, 'dispatch');
  assert.equal(after.deferralExpired, true);
});

test('stale Health slot still waits for a freshly started productive in-flight run', () => {
  const healthTarget = target({
    id: 'workflow-health', workflow: 'workflow-health-snapshot.yml', eventType: 'scheduler-workflow-health', profile: 'observer',
    deferUntilOtherTargetsSettled: { maxMinutes: 20 },
  });
  const healthResult = {
    id: 'workflow-health', workflow: 'workflow-health-snapshot.yml', profile: 'observer', healthBarrier: false,
    decision: 'dispatch', dueAt: '2026-09-04T10:37:00.000Z', latestDueAt: '2026-09-04T17:07:00.000Z',
  };
  const peers = [
    healthResult,
    {
      id: 'league', workflow: 'update-league.yml', profile: 'productive', healthBarrier: true,
      decision: 'in-flight', dueAt: '2026-09-04T17:20:00.000Z', inFlightRunId: 33900269935,
      inFlightCreatedAt: '2026-09-04T17:22:57.000Z',
    },
    {
      id: 'games', workflow: 'update-games.yml', profile: 'productive', healthBarrier: true,
      decision: 'in-flight', dueAt: '2026-09-04T17:00:00.000Z', inFlightRunId: 33900270434,
      inFlightCreatedAt: '2026-09-04T17:22:57.000Z',
    },
  ];
  const result = scheduler.applyTargetDeferral(healthTarget, healthResult, peers, new Date('2026-09-04T17:25:01.000Z'));
  assert.equal(result.decision, 'deferred');
  assert.equal(result.deferralAgeMinutes, 2);
  assert.equal(result.blockingTargets.length, 2);
  assert.equal(result.blockingTargets[0].blockerStartedAt, '2026-09-04T17:22:57.000Z');
});

test('productive in-flight work older than the blocker window no longer starves Health', () => {
  const healthTarget = target({
    id: 'workflow-health', workflow: 'workflow-health-snapshot.yml', eventType: 'scheduler-workflow-health', profile: 'observer',
    deferUntilOtherTargetsSettled: { maxMinutes: 20 },
  });
  const healthResult = {
    id: 'workflow-health', workflow: 'workflow-health-snapshot.yml', profile: 'observer', healthBarrier: false,
    decision: 'dispatch', dueAt: '2026-09-04T17:07:00.000Z',
  };
  const peer = {
    id: 'league', workflow: 'update-league.yml', profile: 'productive', healthBarrier: true,
    decision: 'in-flight', dueAt: '2026-09-04T17:00:00.000Z', inFlightRunId: 10,
    inFlightCreatedAt: '2026-09-04T17:00:00.000Z',
  };
  const result = scheduler.applyTargetDeferral(healthTarget, healthResult, [healthResult, peer], new Date('2026-09-04T17:21:00Z'));
  assert.equal(result.decision, 'dispatch');
  assert.equal(result.deferralExpired, true);
  assert.equal(result.deferralAgeMinutes, 21);
});

test('observation timeout and observation cooldown do not block Health', () => {
  const healthTarget = target({
    id: 'workflow-health', workflow: 'workflow-health-snapshot.yml', eventType: 'scheduler-workflow-health', profile: 'observer',
    deferUntilOtherTargetsSettled: { maxMinutes: 20 },
  });
  const healthResult = {
    id: 'workflow-health', workflow: 'workflow-health-snapshot.yml', profile: 'observer', healthBarrier: false,
    decision: 'dispatch', dueAt: '2026-09-04T13:37:00.000Z',
  };
  for (const decision of ['observation-timeout', 'observation-cooldown']) {
    const result = scheduler.applyTargetDeferral(healthTarget, healthResult, [
      healthResult,
      { id: 'league', workflow: 'update-league.yml', profile: 'productive', healthBarrier: true, decision },
    ], new Date('2026-09-04T13:50:00Z'));
    assert.deepEqual(result, healthResult);
  }
});

test('summary makes missing observation and no-blind-retry behavior explicit', () => {
  const config = { summaryTimezone: 'Europe/Berlin' };
  const markdown = scheduler.buildSummaryMarkdown([
    {
      id: 'league', workflow: 'update-league.yml', profile: 'productive', healthBarrier: true,
      decision: 'awaiting-observation', dueAt: '2026-09-04T13:30:00.000Z', attemptsDispatched: 1, observedAttempts: 0,
      maxAttempts: 3, lastDispatchAt: '2026-09-04T13:32:55.000Z', runQueryFallbackUsed: true, runQueryFallbackRecovered: false,
    },
  ], new Date('2026-09-04T13:39:00Z'), config);
  assert.match(markdown, /Awaiting observation/);
  assert.match(markdown, /no retry is allowed without an observed completed failure/);
  assert.match(markdown, /fallback query also did not recover/);
  assert.match(markdown, /Dispatch observation notes/);
});

test('config requires a positive central dispatch observation timeout', () => {
  const config = {
    schemaVersion: 2,
    repository: 'Lolindhir/fantasy-app',
    lookbackMinutes: 11520,
    summaryTimezone: 'Europe/Berlin',
    dispatchObservation: { timeoutMinutes: 15 },
    state: { schemaVersion: 1, branch: 'workflow-scheduler-state', path: 'workflow-scheduler-state.json' },
    retryPolicies: { standard: { maxAttempts: 3, backoffMinutes: [5, 10], cooldownMinutes: 60 } },
    profiles: { productive: { healthBarrier: true, retryPolicy: 'standard' } },
    targets: [{
      id: 'league', workflow: 'update-league.yml', path: '.github/workflows/update-league.yml', eventType: 'scheduler-update-league',
      profile: 'productive', timezone: 'Etc/UTC', cron: ['*/10 * * * *'], satisfyingEvents: ['repository_dispatch'],
    }],
  };
  scheduler.validateConfig(config);
  config.dispatchObservation.timeoutMinutes = 0;
  assert.throws(() => scheduler.validateConfig(config), /dispatchObservation timeoutMinutes/);
});
