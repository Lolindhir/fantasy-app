'use strict';

const fs = require('node:fs');

function parseField(raw, minimum, maximum) {
  const values = new Set();
  for (const tokenRaw of raw.split(',')) {
    const token = tokenRaw.trim();
    if (!token) throw new Error(`Empty cron token in ${raw}`);

    const [base, stepRaw] = token.split('/', 2);
    const step = stepRaw === undefined ? 1 : Number(stepRaw);
    if (!Number.isInteger(step) || step <= 0) throw new Error(`Invalid cron step: ${token}`);

    let start;
    let end;
    if (base === '*') {
      start = minimum;
      end = maximum;
    } else if (base.includes('-')) {
      [start, end] = base.split('-', 2).map(Number);
    } else {
      start = Number(base);
      end = stepRaw === undefined ? start : maximum;
    }

    if (!Number.isInteger(start) || !Number.isInteger(end) || start < minimum || end > maximum || start > end) {
      throw new Error(`Cron token ${token} is outside ${minimum}-${maximum}`);
    }
    for (let value = start; value <= end; value += step) values.add(value);
  }
  return values;
}

function localParts(date, timeZone) {
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
    hourCycle: 'h23',
    weekday: 'short',
  });
  const parts = Object.fromEntries(formatter.formatToParts(date).map((part) => [part.type, part.value]));
  const weekdayMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  return {
    minute: Number(parts.minute),
    hour: Number(parts.hour),
    day: Number(parts.day),
    month: Number(parts.month),
    weekday: weekdayMap[parts.weekday],
  };
}

function cronMatches(expression, date, timeZone) {
  const fields = expression.trim().split(/\s+/);
  if (fields.length !== 5) throw new Error(`Cron expression must contain five fields: ${expression}`);
  const [minuteRaw, hourRaw, dayRaw, monthRaw, weekdayRaw] = fields;
  const local = localParts(date, timeZone);

  const minuteMatch = parseField(minuteRaw, 0, 59).has(local.minute);
  const hourMatch = parseField(hourRaw, 0, 23).has(local.hour);
  const monthMatch = parseField(monthRaw, 1, 12).has(local.month);
  const dayMatch = parseField(dayRaw, 1, 31).has(local.day);
  const weekdays = parseField(weekdayRaw, 0, 7);
  const weekdayMatch = weekdays.has(local.weekday) || (local.weekday === 0 && weekdays.has(7));

  let dayDimensionMatch;
  if (dayRaw === '*' && weekdayRaw === '*') dayDimensionMatch = true;
  else if (dayRaw === '*') dayDimensionMatch = weekdayMatch;
  else if (weekdayRaw === '*') dayDimensionMatch = dayMatch;
  else dayDimensionMatch = dayMatch || weekdayMatch;

  return minuteMatch && hourMatch && monthMatch && dayDimensionMatch;
}

function latestDueSlot(expressions, timeZone, now, lookbackMinutes) {
  const cursorMs = Math.floor(now.getTime() / 60000) * 60000;
  for (let offset = 0; offset <= lookbackMinutes; offset += 1) {
    const candidate = new Date(cursorMs - offset * 60000);
    if (expressions.some((expression) => cronMatches(expression, candidate, timeZone))) return candidate;
  }
  return null;
}

function runMatchesSlot(run, target, dueAt, ref) {
  if (!(target.satisfyingEvents || []).includes(run.event)) return false;
  if (run.head_branch && run.head_branch !== ref) return false;
  const createdAt = Date.parse(run.created_at || '');
  return Number.isFinite(createdAt) && createdAt >= dueAt.getTime();
}

function runSatisfiesSlot(run, target, dueAt, ref) {
  return runMatchesSlot(run, target, dueAt, ref)
    && run.status === 'completed'
    && run.conclusion === 'success';
}

function runIsInFlightForSlot(run, target, dueAt, ref) {
  return runMatchesSlot(run, target, dueAt, ref)
    && Boolean(run.status)
    && run.status !== 'completed';
}

function schedulerAttemptRuns(runs, target, dueAt, ref) {
  return runs
    .filter((run) => run.event === 'repository_dispatch' && runMatchesSlot(run, target, dueAt, ref))
    .sort((left, right) => Date.parse(right.created_at || '') - Date.parse(left.created_at || ''));
}

function validateConfig(config) {
  if (config.schemaVersion !== 2) throw new Error('Unsupported scheduler schemaVersion');
  if (!Number.isInteger(config.lookbackMinutes) || config.lookbackMinutes < 10080) {
    throw new Error('lookbackMinutes must be at least one week (10080 minutes)');
  }
  if (!config.summaryTimezone) throw new Error('Scheduler config missing summaryTimezone');
  localParts(new Date('2026-01-05T00:00:00Z'), config.summaryTimezone);

  if (!config.state || typeof config.state !== 'object' || Array.isArray(config.state)) {
    throw new Error('Scheduler config missing state contract');
  }
  if (config.state.schemaVersion !== 1 || !config.state.branch || !config.state.path) {
    throw new Error('Invalid scheduler state contract');
  }

  if (!config.retryPolicies || typeof config.retryPolicies !== 'object' || Array.isArray(config.retryPolicies)) {
    throw new Error('Scheduler config must contain retryPolicies');
  }
  for (const [policyId, policy] of Object.entries(config.retryPolicies)) {
    if (!Number.isInteger(policy.maxAttempts) || policy.maxAttempts <= 0) {
      throw new Error(`Invalid maxAttempts for retry policy ${policyId}`);
    }
    if (!Array.isArray(policy.backoffMinutes) || policy.backoffMinutes.length !== Math.max(0, policy.maxAttempts - 1)) {
      throw new Error(`Invalid backoffMinutes for retry policy ${policyId}`);
    }
    if (policy.backoffMinutes.some((minutes) => !Number.isInteger(minutes) || minutes <= 0)) {
      throw new Error(`Invalid backoffMinutes for retry policy ${policyId}`);
    }
    if (!Number.isInteger(policy.cooldownMinutes) || policy.cooldownMinutes <= 0) {
      throw new Error(`Invalid cooldownMinutes for retry policy ${policyId}`);
    }
  }

  if (!config.profiles || typeof config.profiles !== 'object' || Array.isArray(config.profiles)) {
    throw new Error('Scheduler config must contain profiles');
  }
  for (const [profileId, profile] of Object.entries(config.profiles)) {
    if (typeof profile.healthBarrier !== 'boolean') throw new Error(`Invalid healthBarrier for profile ${profileId}`);
    if (!profile.retryPolicy || !config.retryPolicies[profile.retryPolicy]) {
      throw new Error(`Unknown retry policy for profile ${profileId}`);
    }
  }

  if (!Array.isArray(config.targets) || config.targets.length === 0) throw new Error('Scheduler config must contain targets');

  const ids = new Set();
  const workflows = new Set();
  const paths = new Set();
  const events = new Set();
  for (const target of config.targets) {
    for (const key of ['id', 'workflow', 'path', 'eventType', 'profile', 'timezone', 'cron', 'satisfyingEvents']) {
      if (!target[key] || (Array.isArray(target[key]) && target[key].length === 0)) throw new Error(`Target missing ${key}`);
    }
    if (!config.profiles[target.profile]) throw new Error(`Unknown profile ${target.profile} for ${target.id}`);
    if (ids.has(target.id) || workflows.has(target.workflow) || paths.has(target.path) || events.has(target.eventType)) {
      throw new Error(`Duplicate scheduler target identity: ${target.id}`);
    }
    ids.add(target.id);
    workflows.add(target.workflow);
    paths.add(target.path);
    events.add(target.eventType);
    if (!target.path.startsWith('.github/workflows/')) throw new Error(`Invalid workflow path: ${target.path}`);
    if (target.eventType.length > 100) throw new Error(`repository_dispatch eventType is too long: ${target.eventType}`);
    if (target.deferUntilOtherTargetsSettled !== undefined) {
      const deferral = target.deferUntilOtherTargetsSettled;
      if (!deferral || typeof deferral !== 'object' || Array.isArray(deferral)) {
        throw new Error(`Invalid deferUntilOtherTargetsSettled for ${target.id}`);
      }
      if (!Number.isInteger(deferral.maxMinutes) || deferral.maxMinutes <= 0) {
        throw new Error(`Invalid deferral maxMinutes for ${target.id}`);
      }
    }
    localParts(new Date('2026-01-05T00:00:00Z'), target.timezone);
    for (const expression of target.cron) cronMatches(expression, new Date('2026-01-05T00:00:00Z'), target.timezone);
  }
}

function evaluateTarget(target, ref, now, lookbackMinutes, runs) {
  const dueAt = latestDueSlot(target.cron, target.timezone, now, lookbackMinutes);
  if (!dueAt) return { id: target.id, workflow: target.workflow, decision: 'no-due-slot-in-lookback' };
  const satisfying = runs.find((run) => runSatisfiesSlot(run, target, dueAt, ref));
  if (satisfying) {
    return {
      id: target.id,
      workflow: target.workflow,
      decision: 'satisfied',
      dueAt: dueAt.toISOString(),
      satisfyingRunId: satisfying.id,
      satisfyingEvent: satisfying.event,
      satisfyingStatus: satisfying.status,
      satisfyingConclusion: satisfying.conclusion,
    };
  }
  const inFlight = runs.find((run) => runIsInFlightForSlot(run, target, dueAt, ref));
  if (inFlight) {
    return {
      id: target.id,
      workflow: target.workflow,
      decision: 'in-flight',
      dueAt: dueAt.toISOString(),
      inFlightRunId: inFlight.id,
      inFlightEvent: inFlight.event,
      inFlightStatus: inFlight.status,
      inFlightCreatedAt: inFlight.created_at || null,
    };
  }
  return {
    id: target.id,
    workflow: target.workflow,
    decision: 'dispatch',
    dueAt: dueAt.toISOString(),
    eventType: target.eventType,
  };
}

function retryState(dueAt, attemptsDispatched, extra = {}) {
  return {
    dueAt,
    attemptsDispatched,
    lastDispatchAt: extra.lastDispatchAt || null,
    retryNotBefore: extra.retryNotBefore || null,
    circuitOpenUntil: extra.circuitOpenUntil || null,
    lastFailureRunId: extra.lastFailureRunId || null,
    lastFailureConclusion: extra.lastFailureConclusion || null,
  };
}

function evaluateTargetWithRetry(target, profile, retryPolicy, ref, now, lookbackMinutes, runs, targetState = null) {
  const latestDue = latestDueSlot(target.cron, target.timezone, now, lookbackMinutes);
  const base = { id: target.id, workflow: target.workflow, profile: target.profile, healthBarrier: profile.healthBarrier };
  if (!latestDue) return { result: { ...base, decision: 'no-due-slot-in-lookback' }, nextState: null };

  const latestSuccess = runs.find((run) => runSatisfiesSlot(run, target, latestDue, ref));
  if (latestSuccess) {
    return {
      result: {
        ...base,
        decision: 'satisfied',
        dueAt: latestDue.toISOString(),
        satisfyingRunId: latestSuccess.id,
        satisfyingEvent: latestSuccess.event,
        satisfyingStatus: latestSuccess.status,
        satisfyingConclusion: latestSuccess.conclusion,
      },
      nextState: null,
    };
  }

  let state = targetState && typeof targetState === 'object' ? { ...targetState } : null;
  let stateDue = state ? new Date(state.dueAt) : null;
  if (stateDue && !Number.isFinite(stateDue.getTime())) state = null;
  if (stateDue && stateDue.getTime() > now.getTime()) state = null;

  if (state && state.circuitOpenUntil) {
    const recoveryDue = new Date(state.dueAt);
    const recovery = runs.find((run) => runSatisfiesSlot(run, target, recoveryDue, ref));
    if (recovery) {
      state = null;
    } else {
      const circuitOpenUntilMs = Date.parse(state.circuitOpenUntil);
      if (!Number.isFinite(circuitOpenUntilMs)) throw new Error(`Invalid circuitOpenUntil for ${target.id}`);
      if (now.getTime() < circuitOpenUntilMs) {
        return {
          result: {
            ...base,
            decision: 'cooldown',
            dueAt: state.dueAt,
            latestDueAt: latestDue.toISOString(),
            attemptsDispatched: state.attemptsDispatched || retryPolicy.maxAttempts,
            maxAttempts: retryPolicy.maxAttempts,
            circuitOpenUntil: state.circuitOpenUntil,
            lastFailureRunId: state.lastFailureRunId || null,
            lastFailureConclusion: state.lastFailureConclusion || null,
          },
          nextState: state,
        };
      }
      state = null;
    }
  }

  let cycleDue = state ? new Date(state.dueAt) : latestDue;
  let cycleRuns = runs
    .filter((run) => runMatchesSlot(run, target, cycleDue, ref))
    .sort((left, right) => Date.parse(right.created_at || '') - Date.parse(left.created_at || ''));

  const cycleSuccess = cycleRuns.find((run) => run.status === 'completed' && run.conclusion === 'success');
  if (cycleSuccess) {
    const successCreatedAt = Date.parse(cycleSuccess.created_at || '');
    if (Number.isFinite(successCreatedAt) && successCreatedAt >= latestDue.getTime()) {
      return {
        result: {
          ...base,
          decision: 'satisfied',
          dueAt: latestDue.toISOString(),
          satisfyingRunId: cycleSuccess.id,
          satisfyingEvent: cycleSuccess.event,
          satisfyingStatus: cycleSuccess.status,
          satisfyingConclusion: cycleSuccess.conclusion,
        },
        nextState: null,
      };
    }
    state = null;
    cycleDue = latestDue;
    cycleRuns = runs
      .filter((run) => runMatchesSlot(run, target, cycleDue, ref))
      .sort((left, right) => Date.parse(right.created_at || '') - Date.parse(left.created_at || ''));
  }

  const attemptRuns = schedulerAttemptRuns(cycleRuns, target, cycleDue, ref);
  const observedAttempts = attemptRuns.length;
  const attemptsDispatched = Math.max(state?.attemptsDispatched || 0, observedAttempts);
  const latestAttempt = attemptRuns.find((run) => run.status === 'completed') || null;
  const inFlight = cycleRuns.find((run) => Boolean(run.status) && run.status !== 'completed');

  if (inFlight) {
    const nextState = attemptsDispatched > 0
      ? retryState(cycleDue.toISOString(), attemptsDispatched, {
        lastDispatchAt: state?.lastDispatchAt || null,
        lastFailureRunId: state?.lastFailureRunId || null,
        lastFailureConclusion: state?.lastFailureConclusion || null,
      })
      : null;
    return {
      result: {
        ...base,
        decision: 'in-flight',
        dueAt: cycleDue.toISOString(),
        latestDueAt: cycleDue.getTime() === latestDue.getTime() ? undefined : latestDue.toISOString(),
        inFlightRunId: inFlight.id,
        inFlightEvent: inFlight.event,
        inFlightStatus: inFlight.status,
        inFlightCreatedAt: inFlight.created_at || null,
        attemptsDispatched,
        maxAttempts: retryPolicy.maxAttempts,
      },
      nextState,
    };
  }

  if (attemptsDispatched >= retryPolicy.maxAttempts) {
    const anchorMs = Date.parse(latestAttempt?.updated_at || latestAttempt?.created_at || state?.lastDispatchAt || now.toISOString());
    const circuitOpenUntil = new Date((Number.isFinite(anchorMs) ? anchorMs : now.getTime()) + retryPolicy.cooldownMinutes * 60000).toISOString();
    const nextState = retryState(cycleDue.toISOString(), attemptsDispatched, {
      lastDispatchAt: state?.lastDispatchAt || null,
      circuitOpenUntil,
      lastFailureRunId: latestAttempt?.id || state?.lastFailureRunId || null,
      lastFailureConclusion: latestAttempt?.conclusion || state?.lastFailureConclusion || null,
    });
    return {
      result: {
        ...base,
        decision: 'retry-exhausted',
        dueAt: cycleDue.toISOString(),
        latestDueAt: cycleDue.getTime() === latestDue.getTime() ? undefined : latestDue.toISOString(),
        attemptsDispatched,
        maxAttempts: retryPolicy.maxAttempts,
        circuitOpenUntil,
        lastFailureRunId: nextState.lastFailureRunId,
        lastFailureConclusion: nextState.lastFailureConclusion,
      },
      nextState,
    };
  }

  if (attemptsDispatched > 0) {
    const backoffMinutes = retryPolicy.backoffMinutes[attemptsDispatched - 1];
    const anchorMs = Date.parse(latestAttempt?.updated_at || latestAttempt?.created_at || state?.lastDispatchAt || cycleDue.toISOString());
    const retryNotBefore = new Date((Number.isFinite(anchorMs) ? anchorMs : now.getTime()) + backoffMinutes * 60000).toISOString();
    const common = {
      ...base,
      dueAt: cycleDue.toISOString(),
      latestDueAt: cycleDue.getTime() === latestDue.getTime() ? undefined : latestDue.toISOString(),
      attemptsDispatched,
      retryAttempt: attemptsDispatched + 1,
      maxAttempts: retryPolicy.maxAttempts,
      previousRunId: latestAttempt?.id || state?.lastFailureRunId || null,
      previousConclusion: latestAttempt?.conclusion || state?.lastFailureConclusion || null,
      retryNotBefore,
    };
    if (now.getTime() < Date.parse(retryNotBefore)) {
      return {
        result: { ...common, decision: 'retry-wait' },
        nextState: retryState(cycleDue.toISOString(), attemptsDispatched, {
          lastDispatchAt: state?.lastDispatchAt || null,
          retryNotBefore,
          lastFailureRunId: common.previousRunId,
          lastFailureConclusion: common.previousConclusion,
        }),
      };
    }
    return {
      result: { ...common, decision: 'dispatch', eventType: target.eventType },
      nextState: null,
    };
  }

  return {
    result: {
      ...base,
      decision: 'dispatch',
      dueAt: cycleDue.toISOString(),
      latestDueAt: cycleDue.getTime() === latestDue.getTime() ? undefined : latestDue.toISOString(),
      eventType: target.eventType,
      retryAttempt: 1,
      maxAttempts: retryPolicy.maxAttempts,
    },
    nextState: null,
  };
}

function applyTargetDeferral(target, result, peerResults, now) {
  const deferral = target.deferUntilOtherTargetsSettled;
  if (!deferral || result.decision !== 'dispatch') return result;

  const blockers = peerResults
    .filter((peer) => peer.id !== target.id && peer.healthBarrier === true && (peer.decision === 'dispatch' || peer.decision === 'in-flight'))
    .map((peer) => ({
      id: peer.id,
      workflow: peer.workflow,
      profile: peer.profile || null,
      decision: peer.decision,
      dueAt: peer.dueAt || null,
      inFlightRunId: peer.inFlightRunId || null,
    }));
  if (blockers.length === 0) return result;

  const dueAtMs = Date.parse(result.dueAt || '');
  if (!Number.isFinite(dueAtMs)) throw new Error(`Deferred target ${target.id} has invalid dueAt`);
  const ageMs = Math.max(0, now.getTime() - dueAtMs);
  const ageMinutes = Math.floor(ageMs / 60000);
  const annotated = {
    ...result,
    blockingTargets: blockers,
    deferralAgeMinutes: ageMinutes,
    maxDeferralMinutes: deferral.maxMinutes,
  };

  const sameTickDispatchBlockers = blockers.filter((blocker) => blocker.decision === 'dispatch');
  if (sameTickDispatchBlockers.length > 0) {
    return {
      ...annotated,
      decision: 'deferred',
      deferralReason: 'productive-dispatch-this-tick',
      hardDispatchBarrier: true,
    };
  }

  if (ageMs < deferral.maxMinutes * 60000) {
    return { ...annotated, decision: 'deferred', deferralReason: 'productive-in-flight' };
  }
  return { ...annotated, deferralExpired: true, deferralReason: 'in-flight-deferral-expired' };
}

function createEmptySchedulerState(config) {
  return { schemaVersion: config.state.schemaVersion, targets: {} };
}

function validateSchedulerState(state, config) {
  if (!state || typeof state !== 'object' || Array.isArray(state)) throw new Error('Scheduler runtime state is not an object');
  if (state.schemaVersion !== config.state.schemaVersion) throw new Error('Unsupported scheduler runtime state schemaVersion');
  if (!state.targets || typeof state.targets !== 'object' || Array.isArray(state.targets)) throw new Error('Scheduler runtime state targets must be an object');
}

function serializeSchedulerState(state) {
  return `${JSON.stringify(state, null, 2)}\n`;
}

async function loadSchedulerState({ github, context, config, core }) {
  const empty = createEmptySchedulerState(config);
  try {
    const response = await github.rest.repos.getContent({
      owner: context.repo.owner,
      repo: context.repo.repo,
      path: config.state.path,
      ref: config.state.branch,
    });
    if (!response.data || Array.isArray(response.data) || !response.data.content) {
      throw new Error(`Scheduler runtime state ${config.state.branch}/${config.state.path} is not a file`);
    }
    const text = Buffer.from(response.data.content, 'base64').toString('utf8');
    const state = JSON.parse(text);
    validateSchedulerState(state, config);
    return { state, serialized: serializeSchedulerState(state), exists: true };
  } catch (error) {
    if (error && error.status === 404) {
      core.info(`Scheduler runtime state ${config.state.branch}/${config.state.path} does not exist yet; it will be initialized on the first state change.`);
      return { state: empty, serialized: serializeSchedulerState(empty), exists: false };
    }
    throw error;
  }
}

async function persistSchedulerState({ github, context, config, core, state, previousSerialized, existed }) {
  validateSchedulerState(state, config);
  const serialized = serializeSchedulerState(state);
  if (serialized === previousSerialized && existed) return false;
  if (serialized === previousSerialized && !existed && Object.keys(state.targets).length === 0) return false;

  const blob = await github.rest.git.createBlob({
    owner: context.repo.owner,
    repo: context.repo.repo,
    content: serialized,
    encoding: 'utf-8',
  });
  const tree = await github.rest.git.createTree({
    owner: context.repo.owner,
    repo: context.repo.repo,
    tree: [{ path: config.state.path, mode: '100644', type: 'blob', sha: blob.data.sha }],
  });
  const commit = await github.rest.git.createCommit({
    owner: context.repo.owner,
    repo: context.repo.repo,
    message: 'chore(scheduler): update runtime state',
    tree: tree.data.sha,
    parents: [],
  });

  try {
    await github.rest.git.getRef({
      owner: context.repo.owner,
      repo: context.repo.repo,
      ref: `heads/${config.state.branch}`,
    });
    await github.rest.git.updateRef({
      owner: context.repo.owner,
      repo: context.repo.repo,
      ref: `heads/${config.state.branch}`,
      sha: commit.data.sha,
      force: true,
    });
  } catch (error) {
    if (!error || error.status !== 404) throw error;
    await github.rest.git.createRef({
      owner: context.repo.owner,
      repo: context.repo.repo,
      ref: `refs/heads/${config.state.branch}`,
      sha: commit.data.sha,
    });
  }
  core.info(`Scheduler runtime state updated at ${config.state.branch}/${config.state.path}.`);
  return true;
}

function formatTimestamp(value, timeZone) {
  if (!value) return '—';
  const date = value instanceof Date ? value : new Date(value);
  if (!Number.isFinite(date.getTime())) return String(value);
  return new Intl.DateTimeFormat('en-GB', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZoneName: 'short',
  }).format(date);
}

function escapeTableCell(value) {
  return String(value ?? '—').replace(/\|/g, '\\|').replace(/\n/g, ' ');
}

function decisionLabel(result) {
  const labels = {
    satisfied: '✅ Satisfied',
    'in-flight': '⏳ In flight',
    dispatch: result.dispatched ? '🚀 Dispatched' : '🚀 Dispatch',
    deferred: '⏸ Deferred',
    'retry-wait': '🕒 Retry wait',
    'retry-exhausted': '❌ Retry exhausted',
    cooldown: '🧯 Cooldown',
    'no-due-slot-in-lookback': '⚪ No due slot',
  };
  return labels[result.decision] || result.decision;
}

function actionLabel(result) {
  if (result.decision === 'dispatch') return result.dispatched ? 'Started' : 'Start';
  if (result.decision === 'deferred' || result.decision === 'retry-wait') return 'Wait';
  if (result.decision === 'retry-exhausted') return 'Open circuit';
  return 'No action';
}

function reasonForResult(result, timeZone) {
  switch (result.decision) {
    case 'satisfied':
      return `Run #${result.satisfyingRunId} completed successfully.`;
    case 'in-flight':
      return `Run #${result.inFlightRunId} is ${result.inFlightStatus || 'in flight'}.`;
    case 'dispatch':
      if (result.deferralExpired) {
        const blockers = (result.blockingTargets || []).map((item) => `${item.id} (${item.decision})`).join(', ');
        return `Health starts because the ${result.maxDeferralMinutes}-minute in-flight deferral limit expired${blockers ? `; still running: ${blockers}` : ''}.`;
      }
      if ((result.retryAttempt || 1) > 1) {
        return `Retry ${result.retryAttempt}/${result.maxAttempts} after run #${result.previousRunId || '?'} ended ${result.previousConclusion || 'unsuccessfully'}.`;
      }
      return 'Due slot has no successful or in-flight run.';
    case 'retry-wait':
      return `Attempt ${result.attemptsDispatched}/${result.maxAttempts} ended ${result.previousConclusion || 'unsuccessfully'}; retry eligible at ${formatTimestamp(result.retryNotBefore, timeZone)}.`;
    case 'retry-exhausted':
      return `${result.attemptsDispatched}/${result.maxAttempts} attempts exhausted; circuit open until ${formatTimestamp(result.circuitOpenUntil, timeZone)}.`;
    case 'cooldown':
      return `Retry circuit remains open until ${formatTimestamp(result.circuitOpenUntil, timeZone)}.`;
    case 'deferred': {
      const blockers = (result.blockingTargets || []).map((item) => `${item.id} (${item.decision})`).join(', ');
      if (result.hardDispatchBarrier) return `Health waits because productive work starts this tick: ${blockers}.`;
      return `Health waits for productive in-flight work: ${blockers}.`;
    }
    case 'no-due-slot-in-lookback':
      return 'No matching schedule slot exists in the configured lookback.';
    default:
      return result.deferralExpired ? 'In-flight deferral limit expired.' : 'See machine-readable log.';
  }
}

function buildSummaryMarkdown(results, now, config) {
  const timeZone = config.summaryTimezone;
  const dispatched = results.filter((result) => result.dispatched).length;
  const deferred = results.filter((result) => result.decision === 'deferred').length;
  const retryStates = results.filter((result) => ['retry-wait', 'retry-exhausted', 'cooldown'].includes(result.decision)).length;
  const satisfied = results.filter((result) => result.decision === 'satisfied').length;
  const inFlight = results.filter((result) => result.decision === 'in-flight').length;

  let markdown = `## Scheduler summary — ${formatTimestamp(now, timeZone)}\n\n`;
  markdown += `**${dispatched} dispatched · ${deferred} deferred · ${retryStates} retry/cooldown · ${inFlight} in flight · ${satisfied} satisfied**\n\n`;
  markdown += '| Target | Profile | Status | Action | Due slot | Attempt | Reason |\n';
  markdown += '| --- | --- | --- | --- | --- | --- | --- |\n';
  for (const result of results) {
    const attempts = result.maxAttempts
      ? `${result.retryAttempt || result.attemptsDispatched || '—'}/${result.maxAttempts}`
      : '—';
    markdown += `| ${escapeTableCell(result.id)} | ${escapeTableCell(result.profile || '—')} | ${escapeTableCell(decisionLabel(result))} | ${escapeTableCell(actionLabel(result))} | ${escapeTableCell(formatTimestamp(result.dueAt, timeZone))} | ${escapeTableCell(attempts)} | ${escapeTableCell(reasonForResult(result, timeZone))} |\n`;
  }

  const deferredHealth = results.find((result) => result.id === 'workflow-health' && result.decision === 'deferred');
  if (deferredHealth) {
    markdown += `\n### Why Health waited\n\n${reasonForResult(deferredHealth, timeZone)}\n`;
  }
  const circuits = results.filter((result) => ['retry-exhausted', 'cooldown'].includes(result.decision));
  if (circuits.length > 0) {
    markdown += '\n### Retry / circuit-breaker notes\n\n';
    for (const result of circuits) markdown += `- **${result.id}:** ${reasonForResult(result, timeZone)}\n`;
  }
  markdown += '\n<details><summary>Machine-readable decisions</summary>\n\n```json\n';
  markdown += `${JSON.stringify(results, null, 2)}\n`;
  markdown += '```\n</details>\n';
  return markdown;
}

async function writeSummary(core, results, now, config) {
  if (!core.summary || typeof core.summary.addRaw !== 'function') return;
  await core.summary.addRaw(buildSummaryMarkdown(results, now, config)).write();
}

async function run({ github, context, core, configPath = '.github/workflow-schedules.json', now = new Date() }) {
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  validateConfig(config);
  if (config.repository !== `${context.repo.owner}/${context.repo.repo}`) {
    throw new Error(`Scheduler repository mismatch: config=${config.repository} runtime=${context.repo.owner}/${context.repo.repo}`);
  }
  const ref = config.ref || 'main';
  const loadedState = await loadSchedulerState({ github, context, config, core });
  const runtimeState = JSON.parse(JSON.stringify(loadedState.state));
  const failures = [];
  const evaluated = [];

  for (const target of config.targets) {
    try {
      const response = await github.rest.actions.listWorkflowRuns({
        owner: context.repo.owner,
        repo: context.repo.repo,
        workflow_id: target.workflow,
        branch: ref,
        per_page: 100,
      });
      const profile = config.profiles[target.profile];
      const retryPolicy = config.retryPolicies[profile.retryPolicy];
      const evaluation = evaluateTargetWithRetry(
        target,
        profile,
        retryPolicy,
        ref,
        now,
        config.lookbackMinutes,
        response.data.workflow_runs || [],
        runtimeState.targets[target.id] || null,
      );
      if (evaluation.nextState) runtimeState.targets[target.id] = evaluation.nextState;
      else delete runtimeState.targets[target.id];
      evaluated.push({ target, result: evaluation.result });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      core.error(`${target.id}: ${message}`);
      failures.push(`${target.id}: ${message}`);
    }
  }

  const peerResults = evaluated.map((item) => item.result);
  for (const item of evaluated) {
    item.result = applyTargetDeferral(item.target, item.result, peerResults, now);
    if (item.result.decision === 'deferred') {
      const existing = runtimeState.targets[item.target.id] || null;
      runtimeState.targets[item.target.id] = retryState(item.result.dueAt, existing?.attemptsDispatched || 0, {
        lastDispatchAt: existing?.lastDispatchAt || null,
        retryNotBefore: existing?.retryNotBefore || null,
        circuitOpenUntil: existing?.circuitOpenUntil || null,
        lastFailureRunId: existing?.lastFailureRunId || null,
        lastFailureConclusion: existing?.lastFailureConclusion || null,
      });
    }
  }

  const dispatchOrder = [...evaluated].sort((left, right) => {
    const leftDeferred = left.target.deferUntilOtherTargetsSettled ? 1 : 0;
    const rightDeferred = right.target.deferUntilOtherTargetsSettled ? 1 : 0;
    return leftDeferred - rightDeferred;
  });
  const results = [];

  for (const { target, result } of dispatchOrder) {
    try {
      if (result.decision === 'dispatch') {
        await github.rest.repos.createDispatchEvent({
          owner: context.repo.owner,
          repo: context.repo.repo,
          event_type: target.eventType,
          client_payload: {
            scheduler_id: target.id,
            workflow: target.workflow,
            due_at: result.dueAt,
            requested_at: now.toISOString(),
            retry_attempt: result.retryAttempt || 1,
            max_attempts: result.maxAttempts || null,
            ref,
          },
        });
        result.dispatched = true;
        runtimeState.targets[target.id] = retryState(result.dueAt, result.retryAttempt || 1, {
          lastDispatchAt: now.toISOString(),
          lastFailureRunId: result.previousRunId || null,
          lastFailureConclusion: result.previousConclusion || null,
        });
      }
      core.info(JSON.stringify(result));
      results.push(result);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      core.error(`${target.id}: ${message}`);
      failures.push(`${target.id}: ${message}`);
    }
  }

  try {
    await persistSchedulerState({
      github,
      context,
      config,
      core,
      state: runtimeState,
      previousSerialized: loadedState.serialized,
      existed: loadedState.exists,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    core.error(`scheduler-state: ${message}`);
    failures.push(`scheduler-state: ${message}`);
  }

  try {
    await writeSummary(core, results, now, config);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    core.warning(`Could not write scheduler summary: ${message}`);
  }

  if (failures.length) throw new Error(`Scheduler target errors: ${failures.join(' | ')}`);
  return results;
}

module.exports = {
  applyTargetDeferral,
  buildSummaryMarkdown,
  createEmptySchedulerState,
  cronMatches,
  evaluateTarget,
  evaluateTargetWithRetry,
  latestDueSlot,
  loadSchedulerState,
  localParts,
  parseField,
  persistSchedulerState,
  reasonForResult,
  run,
  runIsInFlightForSlot,
  runMatchesSlot,
  runSatisfiesSlot,
  schedulerAttemptRuns,
  serializeSchedulerState,
  validateConfig,
  validateSchedulerState,
};
