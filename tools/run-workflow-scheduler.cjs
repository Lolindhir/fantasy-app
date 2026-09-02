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

function runSatisfiesSlot(run, target, dueAt, ref) {
  if (!(target.satisfyingEvents || []).includes(run.event)) return false;
  if (run.head_branch && run.head_branch !== ref) return false;
  const createdAt = Date.parse(run.created_at || '');
  return Number.isFinite(createdAt) && createdAt >= dueAt.getTime();
}

function validateConfig(config) {
  if (config.schemaVersion !== 1) throw new Error('Unsupported scheduler schemaVersion');
  if (!Number.isInteger(config.lookbackMinutes) || config.lookbackMinutes < 10080) {
    throw new Error('lookbackMinutes must be at least one week (10080 minutes)');
  }
  if (!Array.isArray(config.targets) || config.targets.length === 0) throw new Error('Scheduler config must contain targets');

  const ids = new Set();
  const workflows = new Set();
  const paths = new Set();
  const events = new Set();
  for (const target of config.targets) {
    for (const key of ['id', 'workflow', 'path', 'eventType', 'timezone', 'cron', 'satisfyingEvents']) {
      if (!target[key] || (Array.isArray(target[key]) && target[key].length === 0)) throw new Error(`Target missing ${key}`);
    }
    if (ids.has(target.id) || workflows.has(target.workflow) || paths.has(target.path) || events.has(target.eventType)) {
      throw new Error(`Duplicate scheduler target identity: ${target.id}`);
    }
    ids.add(target.id);
    workflows.add(target.workflow);
    paths.add(target.path);
    events.add(target.eventType);
    if (!target.path.startsWith('.github/workflows/')) throw new Error(`Invalid workflow path: ${target.path}`);
    if (target.eventType.length > 100) throw new Error(`repository_dispatch eventType is too long: ${target.eventType}`);
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
  return {
    id: target.id,
    workflow: target.workflow,
    decision: 'dispatch',
    dueAt: dueAt.toISOString(),
    eventType: target.eventType,
  };
}

async function run({ github, context, core, configPath = '.github/workflow-schedules.json', now = new Date() }) {
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  validateConfig(config);
  if (config.repository !== `${context.repo.owner}/${context.repo.repo}`) {
    throw new Error(`Scheduler repository mismatch: config=${config.repository} runtime=${context.repo.owner}/${context.repo.repo}`);
  }
  const ref = config.ref || 'main';
  const failures = [];
  const results = [];

  for (const target of config.targets) {
    try {
      const response = await github.rest.actions.listWorkflowRuns({
        owner: context.repo.owner,
        repo: context.repo.repo,
        workflow_id: target.workflow,
        branch: ref,
        per_page: 100,
      });
      const result = evaluateTarget(target, ref, now, config.lookbackMinutes, response.data.workflow_runs || []);
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
            ref,
          },
        });
        result.dispatched = true;
      }
      core.info(JSON.stringify(result));
      results.push(result);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      core.error(`${target.id}: ${message}`);
      failures.push(`${target.id}: ${message}`);
    }
  }

  if (failures.length) throw new Error(`Scheduler target errors: ${failures.join(' | ')}`);
  return results;
}

module.exports = {
  cronMatches,
  evaluateTarget,
  latestDueSlot,
  localParts,
  parseField,
  run,
  runSatisfiesSlot,
  validateConfig,
};
