'use strict';

const fs = require('node:fs');
const base = require('./run-workflow-scheduler.cjs');

const OBSERVATION_DECISIONS = new Set(['awaiting-observation', 'observation-timeout', 'observation-cooldown']);

function validateConfig(config) {
  base.validateConfig(config);
  if (!config.dispatchObservation || typeof config.dispatchObservation !== 'object' || Array.isArray(config.dispatchObservation)
    || !Number.isInteger(config.dispatchObservation.timeoutMinutes) || config.dispatchObservation.timeoutMinutes <= 0) {
    throw new Error('Invalid dispatchObservation timeoutMinutes');
  }
}

function retryState(dueAt, attemptsDispatched, extra = {}) {
  return {
    dueAt,
    attemptsDispatched,
    lastDispatchAt: extra.lastDispatchAt || null,
    retryNotBefore: extra.retryNotBefore || null,
    circuitOpenUntil: extra.circuitOpenUntil || null,
    circuitReason: extra.circuitReason || null,
    lastFailureRunId: extra.lastFailureRunId || null,
    lastFailureConclusion: extra.lastFailureConclusion || null,
  };
}

function mergeWorkflowRuns(...groups) {
  const byId = new Map();
  for (const runs of groups) {
    for (const run of runs || []) {
      const key = run.id === undefined || run.id === null
        ? `${run.event || ''}:${run.created_at || ''}:${run.head_sha || ''}`
        : String(run.id);
      if (!byId.has(key)) byId.set(key, run);
    }
  }
  return [...byId.values()].sort((left, right) => Date.parse(right.created_at || '') - Date.parse(left.created_at || ''));
}

function observationDecision(baseResult, cycleDue, latestDue, retryPolicy, state, observedAttempts, now) {
  const lastDispatchAtMs = Date.parse(state?.lastDispatchAt || '');
  const timeoutMinutes = retryPolicy.dispatchObservationTimeoutMinutes;
  const timeoutMs = timeoutMinutes * 60000;
  const timeoutAt = Number.isFinite(lastDispatchAtMs)
    ? new Date(lastDispatchAtMs + timeoutMs).toISOString()
    : null;
  const common = {
    ...baseResult,
    dueAt: cycleDue.toISOString(),
    latestDueAt: cycleDue.getTime() === latestDue.getTime() ? undefined : latestDue.toISOString(),
    attemptsDispatched: state?.attemptsDispatched || 0,
    observedAttempts,
    unobservedDispatches: Math.max(0, (state?.attemptsDispatched || 0) - observedAttempts),
    maxAttempts: retryPolicy.maxAttempts,
    lastDispatchAt: state?.lastDispatchAt || null,
    observationTimeoutMinutes: timeoutMinutes,
    observationTimeoutAt: timeoutAt,
  };

  if (!Number.isFinite(lastDispatchAtMs) || now.getTime() < lastDispatchAtMs + timeoutMs) {
    return { result: { ...common, decision: 'awaiting-observation' }, nextState: state };
  }

  const circuitOpenUntilMs = lastDispatchAtMs + timeoutMs + retryPolicy.cooldownMinutes * 60000;
  if (now.getTime() >= circuitOpenUntilMs) return null;

  const circuitOpenUntil = new Date(circuitOpenUntilMs).toISOString();
  const nextState = retryState(cycleDue.toISOString(), state.attemptsDispatched, {
    lastDispatchAt: state.lastDispatchAt,
    circuitOpenUntil,
    circuitReason: 'dispatch-observation-timeout',
    lastFailureRunId: state.lastFailureRunId || null,
    lastFailureConclusion: state.lastFailureConclusion || null,
  });
  return {
    result: {
      ...common,
      decision: state.circuitReason === 'dispatch-observation-timeout' ? 'observation-cooldown' : 'observation-timeout',
      circuitOpenUntil,
      circuitReason: 'dispatch-observation-timeout',
    },
    nextState,
  };
}

function evaluateTargetWithRetry(target, profile, retryPolicy, ref, now, lookbackMinutes, runs, targetState = null) {
  const latestDue = base.latestDueSlot(target.cron, target.timezone, now, lookbackMinutes);
  const baseResult = { id: target.id, workflow: target.workflow, profile: target.profile, healthBarrier: profile.healthBarrier };
  if (!latestDue) return { result: { ...baseResult, decision: 'no-due-slot-in-lookback' }, nextState: null };

  const latestSuccess = runs.find((run) => base.runSatisfiesSlot(run, target, latestDue, ref));
  if (latestSuccess) {
    return {
      result: {
        ...baseResult,
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
    const recovery = runs.find((run) => base.runSatisfiesSlot(run, target, recoveryDue, ref));
    if (recovery) {
      state = null;
    } else {
      const circuitOpenUntilMs = Date.parse(state.circuitOpenUntil);
      if (!Number.isFinite(circuitOpenUntilMs)) throw new Error(`Invalid circuitOpenUntil for ${target.id}`);
      if (now.getTime() < circuitOpenUntilMs) {
        const observationCircuit = state.circuitReason === 'dispatch-observation-timeout';
        return {
          result: {
            ...baseResult,
            decision: observationCircuit ? 'observation-cooldown' : 'cooldown',
            dueAt: state.dueAt,
            latestDueAt: latestDue.toISOString(),
            attemptsDispatched: state.attemptsDispatched || retryPolicy.maxAttempts,
            observedAttempts: observationCircuit ? base.schedulerAttemptRuns(runs, target, recoveryDue, ref).length : undefined,
            maxAttempts: retryPolicy.maxAttempts,
            circuitOpenUntil: state.circuitOpenUntil,
            circuitReason: state.circuitReason || 'retry-exhausted',
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
    .filter((run) => base.runMatchesSlot(run, target, cycleDue, ref))
    .sort((left, right) => Date.parse(right.created_at || '') - Date.parse(left.created_at || ''));

  const cycleSuccess = cycleRuns.find((run) => run.status === 'completed' && run.conclusion === 'success');
  if (cycleSuccess) {
    const successCreatedAt = Date.parse(cycleSuccess.created_at || '');
    if (Number.isFinite(successCreatedAt) && successCreatedAt >= latestDue.getTime()) {
      return {
        result: {
          ...baseResult,
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
      .filter((run) => base.runMatchesSlot(run, target, cycleDue, ref))
      .sort((left, right) => Date.parse(right.created_at || '') - Date.parse(left.created_at || ''));
  }

  const attemptRuns = base.schedulerAttemptRuns(cycleRuns, target, cycleDue, ref);
  const observedAttempts = attemptRuns.length;
  const stateAttempts = state?.attemptsDispatched || 0;
  const attemptsDispatched = Math.max(stateAttempts, observedAttempts);
  const latestAttempt = attemptRuns[0] || null;
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
        ...baseResult,
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

  if (state && stateAttempts > observedAttempts) {
    const observation = observationDecision(baseResult, cycleDue, latestDue, retryPolicy, state, observedAttempts, now);
    if (observation) return observation;
    return evaluateTargetWithRetry(target, profile, retryPolicy, ref, now, lookbackMinutes, runs, null);
  }

  const latestAttemptFailed = latestAttempt
    && latestAttempt.status === 'completed'
    && latestAttempt.conclusion !== 'success';

  if (attemptsDispatched >= retryPolicy.maxAttempts && latestAttemptFailed) {
    const anchorMs = Date.parse(latestAttempt.updated_at || latestAttempt.created_at || now.toISOString());
    const circuitOpenUntil = new Date((Number.isFinite(anchorMs) ? anchorMs : now.getTime()) + retryPolicy.cooldownMinutes * 60000).toISOString();
    const nextState = retryState(cycleDue.toISOString(), attemptsDispatched, {
      lastDispatchAt: state?.lastDispatchAt || null,
      circuitOpenUntil,
      circuitReason: 'retry-exhausted',
      lastFailureRunId: latestAttempt.id,
      lastFailureConclusion: latestAttempt.conclusion,
    });
    return {
      result: {
        ...baseResult,
        decision: 'retry-exhausted',
        dueAt: cycleDue.toISOString(),
        latestDueAt: cycleDue.getTime() === latestDue.getTime() ? undefined : latestDue.toISOString(),
        attemptsDispatched,
        maxAttempts: retryPolicy.maxAttempts,
        circuitOpenUntil,
        circuitReason: 'retry-exhausted',
        lastFailureRunId: latestAttempt.id,
        lastFailureConclusion: latestAttempt.conclusion,
      },
      nextState,
    };
  }

  if (attemptsDispatched > 0 && latestAttemptFailed) {
    const backoffMinutes = retryPolicy.backoffMinutes[attemptsDispatched - 1];
    const anchorMs = Date.parse(latestAttempt.updated_at || latestAttempt.created_at || cycleDue.toISOString());
    const retryNotBefore = new Date((Number.isFinite(anchorMs) ? anchorMs : now.getTime()) + backoffMinutes * 60000).toISOString();
    const common = {
      ...baseResult,
      dueAt: cycleDue.toISOString(),
      latestDueAt: cycleDue.getTime() === latestDue.getTime() ? undefined : latestDue.toISOString(),
      attemptsDispatched,
      retryAttempt: attemptsDispatched + 1,
      maxAttempts: retryPolicy.maxAttempts,
      previousRunId: latestAttempt.id,
      previousConclusion: latestAttempt.conclusion,
      retryNotBefore,
    };
    if (now.getTime() < Date.parse(retryNotBefore)) {
      return {
        result: { ...common, decision: 'retry-wait' },
        nextState: retryState(cycleDue.toISOString(), attemptsDispatched, {
          lastDispatchAt: state?.lastDispatchAt || null,
          retryNotBefore,
          lastFailureRunId: latestAttempt.id,
          lastFailureConclusion: latestAttempt.conclusion,
        }),
      };
    }
    return { result: { ...common, decision: 'dispatch', eventType: target.eventType }, nextState: null };
  }

  if (attemptsDispatched > 0) {
    const safetyState = state || retryState(cycleDue.toISOString(), attemptsDispatched, {
      lastDispatchAt: latestAttempt?.created_at || null,
    });
    return {
      result: {
        ...baseResult,
        decision: 'awaiting-observation',
        dueAt: cycleDue.toISOString(),
        latestDueAt: cycleDue.getTime() === latestDue.getTime() ? undefined : latestDue.toISOString(),
        attemptsDispatched,
        observedAttempts,
        unobservedDispatches: Math.max(0, attemptsDispatched - observedAttempts),
        maxAttempts: retryPolicy.maxAttempts,
        lastDispatchAt: safetyState.lastDispatchAt,
        observationTimeoutMinutes: retryPolicy.dispatchObservationTimeoutMinutes,
      },
      nextState: safetyState,
    };
  }

  return {
    result: {
      ...baseResult,
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

async function evaluateTargetFromGithub({ github, context, target, profile, retryPolicy, ref, now, lookbackMinutes, targetState }) {
  const primaryResponse = await github.rest.actions.listWorkflowRuns({
    owner: context.repo.owner,
    repo: context.repo.repo,
    workflow_id: target.workflow,
    branch: ref,
    per_page: 100,
  });
  const primaryRuns = primaryResponse.data.workflow_runs || [];
  let evaluation = evaluateTargetWithRetry(target, profile, retryPolicy, ref, now, lookbackMinutes, primaryRuns, targetState);
  if (!OBSERVATION_DECISIONS.has(evaluation.result.decision)) return evaluation;

  const fallbackResponse = await github.rest.actions.listWorkflowRuns({
    owner: context.repo.owner,
    repo: context.repo.repo,
    workflow_id: target.workflow,
    event: 'repository_dispatch',
    per_page: 100,
  });
  const fallbackRuns = fallbackResponse.data.workflow_runs || [];
  const mergedRuns = mergeWorkflowRuns(primaryRuns, fallbackRuns);
  evaluation = evaluateTargetWithRetry(target, profile, retryPolicy, ref, now, lookbackMinutes, mergedRuns, targetState);
  evaluation.result.runQueryFallbackUsed = true;
  evaluation.result.runQueryFallbackRecovered = !OBSERVATION_DECISIONS.has(evaluation.result.decision);
  evaluation.result.primaryRunCount = primaryRuns.length;
  evaluation.result.fallbackRunCount = fallbackRuns.length;
  return evaluation;
}

function applyTargetDeferral(target, result, peerResults, now) {
  const deferral = target.deferUntilOtherTargetsSettled;
  if (!deferral || result.decision !== 'dispatch') return result;

  const blockerDecisions = new Set(['dispatch', 'in-flight', 'awaiting-observation']);
  const blockers = peerResults
    .filter((peer) => peer.id !== target.id && peer.healthBarrier === true && blockerDecisions.has(peer.decision))
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
  const annotated = {
    ...result,
    blockingTargets: blockers,
    deferralAgeMinutes: Math.floor(ageMs / 60000),
    maxDeferralMinutes: deferral.maxMinutes,
  };

  if (blockers.some((blocker) => blocker.decision === 'dispatch')) {
    return { ...annotated, decision: 'deferred', deferralReason: 'productive-dispatch-this-tick', hardDispatchBarrier: true };
  }
  if (ageMs < deferral.maxMinutes * 60000) {
    return { ...annotated, decision: 'deferred', deferralReason: 'productive-in-flight-or-unobserved' };
  }
  return { ...annotated, deferralExpired: true, deferralReason: 'in-flight-or-observation-deferral-expired' };
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
    'awaiting-observation': '👀 Awaiting observation',
    'observation-timeout': '⚠️ Observation timeout',
    'observation-cooldown': '🛰 Observation cooldown',
    'no-due-slot-in-lookback': '⚪ No due slot',
  };
  return labels[result.decision] || result.decision;
}

function actionLabel(result) {
  if (result.decision === 'dispatch') return result.dispatched ? 'Started' : 'Start';
  if (['deferred', 'retry-wait', 'awaiting-observation'].includes(result.decision)) return 'Wait';
  if (result.decision === 'retry-exhausted') return 'Open circuit';
  if (result.decision === 'observation-timeout') return 'Open observation circuit';
  return 'No action';
}

function appendFallback(result, text) {
  if (!result.runQueryFallbackUsed) return text;
  return result.runQueryFallbackRecovered
    ? `${text} Recovered through the unfiltered repository_dispatch fallback query.`
    : `${text} The unfiltered repository_dispatch fallback query also did not recover the expected run.`;
}

function reasonForResult(result, timeZone) {
  let text;
  switch (result.decision) {
    case 'satisfied':
      text = `Run #${result.satisfyingRunId} completed successfully.`;
      break;
    case 'in-flight':
      text = `Run #${result.inFlightRunId} is ${result.inFlightStatus || 'in flight'}.`;
      break;
    case 'dispatch':
      if (result.deferralExpired) {
        const blockers = (result.blockingTargets || []).map((item) => `${item.id} (${item.decision})`).join(', ');
        text = `Health starts because the ${result.maxDeferralMinutes}-minute observation deferral limit expired${blockers ? `; still unresolved: ${blockers}` : ''}.`;
      } else if ((result.retryAttempt || 1) > 1) {
        text = `Retry ${result.retryAttempt}/${result.maxAttempts} after observed run #${result.previousRunId} ended ${result.previousConclusion}.`;
      } else {
        text = 'Due slot has no successful or in-flight run.';
      }
      break;
    case 'retry-wait':
      text = `Observed attempt ${result.attemptsDispatched}/${result.maxAttempts} ended ${result.previousConclusion}; retry eligible at ${formatTimestamp(result.retryNotBefore, timeZone)}.`;
      break;
    case 'retry-exhausted':
      text = `${result.attemptsDispatched}/${result.maxAttempts} observed failed attempts exhausted; circuit open until ${formatTimestamp(result.circuitOpenUntil, timeZone)}.`;
      break;
    case 'cooldown':
      text = `Retry circuit remains open until ${formatTimestamp(result.circuitOpenUntil, timeZone)}.`;
      break;
    case 'awaiting-observation':
      text = `Dispatch attempt ${result.attemptsDispatched}/${result.maxAttempts} was requested at ${formatTimestamp(result.lastDispatchAt, timeZone)} but is not visible in the current workflow-run results; no retry is allowed without an observed completed failure.`;
      break;
    case 'observation-timeout':
      text = `Dispatch remained unobserved for ${result.observationTimeoutMinutes} minutes; no blind retry was started. Observation circuit is open until ${formatTimestamp(result.circuitOpenUntil, timeZone)}.`;
      break;
    case 'observation-cooldown':
      text = `Expected dispatch is still not observable; blind retries remain suppressed until ${formatTimestamp(result.circuitOpenUntil, timeZone)}.`;
      break;
    case 'deferred': {
      const blockers = (result.blockingTargets || []).map((item) => `${item.id} (${item.decision})`).join(', ');
      text = result.hardDispatchBarrier
        ? `Health waits because productive work starts this tick: ${blockers}.`
        : `Health waits for productive work that is running or awaiting observation: ${blockers}.`;
      break;
    }
    case 'no-due-slot-in-lookback':
      text = 'No matching schedule slot exists in the configured lookback.';
      break;
    default:
      text = result.deferralExpired ? 'Observation deferral limit expired.' : 'See machine-readable log.';
  }
  return appendFallback(result, text);
}

function buildSummaryMarkdown(results, now, config) {
  const timeZone = config.summaryTimezone;
  const dispatched = results.filter((result) => result.dispatched).length;
  const deferred = results.filter((result) => result.decision === 'deferred').length;
  const retryStates = results.filter((result) => ['retry-wait', 'retry-exhausted', 'cooldown'].includes(result.decision)).length;
  const observationStates = results.filter((result) => OBSERVATION_DECISIONS.has(result.decision)).length;
  const satisfied = results.filter((result) => result.decision === 'satisfied').length;
  const inFlight = results.filter((result) => result.decision === 'in-flight').length;

  let markdown = `## Scheduler summary — ${formatTimestamp(now, timeZone)}\n\n`;
  markdown += `**${dispatched} dispatched · ${deferred} deferred · ${retryStates} retry/cooldown · ${observationStates} observation · ${inFlight} in flight · ${satisfied} satisfied**\n\n`;
  markdown += '| Target | Profile | Status | Action | Due slot | Attempt | Reason |\n';
  markdown += '| --- | --- | --- | --- | --- | --- | --- |\n';
  for (const result of results) {
    const attempts = result.maxAttempts ? `${result.retryAttempt || result.attemptsDispatched || '—'}/${result.maxAttempts}` : '—';
    markdown += `| ${escapeTableCell(result.id)} | ${escapeTableCell(result.profile || '—')} | ${escapeTableCell(decisionLabel(result))} | ${escapeTableCell(actionLabel(result))} | ${escapeTableCell(formatTimestamp(result.dueAt, timeZone))} | ${escapeTableCell(attempts)} | ${escapeTableCell(reasonForResult(result, timeZone))} |\n`;
  }

  const deferredHealth = results.find((result) => result.id === 'workflow-health' && result.decision === 'deferred');
  if (deferredHealth) markdown += `\n### Why Health waited\n\n${reasonForResult(deferredHealth, timeZone)}\n`;
  const observations = results.filter((result) => OBSERVATION_DECISIONS.has(result.decision));
  if (observations.length > 0) {
    markdown += '\n### Dispatch observation notes\n\n';
    for (const result of observations) markdown += `- **${result.id}:** ${reasonForResult(result, timeZone)}\n`;
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
  const loadedState = await base.loadSchedulerState({ github, context, config, core });
  const runtimeState = JSON.parse(JSON.stringify(loadedState.state));
  const failures = [];
  const evaluated = [];

  for (const target of config.targets) {
    try {
      const profile = config.profiles[target.profile];
      const retryPolicy = {
        ...config.retryPolicies[profile.retryPolicy],
        dispatchObservationTimeoutMinutes: config.dispatchObservation.timeoutMinutes,
      };
      const evaluation = await evaluateTargetFromGithub({
        github,
        context,
        target,
        profile,
        retryPolicy,
        ref,
        now,
        lookbackMinutes: config.lookbackMinutes,
        targetState: runtimeState.targets[target.id] || null,
      });
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
        circuitReason: existing?.circuitReason || null,
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
    await base.persistSchedulerState({
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
  ...base,
  applyTargetDeferral,
  buildSummaryMarkdown,
  evaluateTargetFromGithub,
  evaluateTargetWithRetry,
  mergeWorkflowRuns,
  reasonForResult,
  run,
  validateConfig,
};
