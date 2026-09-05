'use strict';

const runtime = require('./run-workflow-scheduler-runtime.cjs');

const MACHINE_MARKER = '\n<details><summary>Machine-readable decisions</summary>\n\n```json\n';
const MACHINE_SUFFIX = '```\n</details>\n';

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

function issueLabel(issueNumbers) {
  if (!Array.isArray(issueNumbers) || issueNumbers.length === 0) return 'none';
  return issueNumbers.map((number) => `#${number}`).join(', ');
}

function projectDecisionLabel(result) {
  const labels = {
    idle: '⚪ Idle',
    debounce: '🕒 Debouncing',
    'in-flight': '⏳ Batch in flight',
    dispatch: result.dispatched ? '🚀 Batch dispatched' : '🚀 Batch dispatch',
    error: '❌ Detector error',
  };
  return labels[result.decision] || result.decision;
}

function projectActionLabel(result) {
  if (result.decision === 'dispatch') return result.dispatched ? 'Started one batch' : 'Start one batch';
  if (result.decision === 'debounce') return 'Wait for quiet/max-wait';
  if (result.decision === 'in-flight') return 'Suppress duplicate';
  if (result.decision === 'error') return 'Fail scheduler tick';
  return 'No action';
}

function projectReason(result, timeZone, config) {
  const sync = config.projectFieldSync || {};
  const count = Array.isArray(result.issueNumbers) ? result.issueNumbers.length : 0;
  const noun = count === 1 ? 'Issue' : 'Issues';

  switch (result.decision) {
    case 'idle':
      return `No Issue changed after the Project-sync watermark at ${formatTimestamp(result.since, timeZone)}.`;
    case 'debounce':
      return `${count} changed ${noun} pending; latest update ${formatTimestamp(result.latestUpdateAt, timeZone)}, quiet ${result.quietAgeMinutes ?? '—'}/${sync.quietMinutes ?? '—'} min, batch age ${result.pendingAgeMinutes ?? '—'}/${sync.maxWaitMinutes ?? '—'} min.`;
    case 'in-flight':
      return `Project batch run #${result.inFlightRunId} is already in flight; a duplicate batch is suppressed.`;
    case 'dispatch':
      if (result.dispatchReason === 'max-wait-reached') {
        return `${count} changed ${noun} were grouped into one batch because the ${sync.maxWaitMinutes ?? 'configured'}-minute maximum wait was reached.`;
      }
      return `${count} changed ${noun} were grouped into one batch after the ${sync.quietMinutes ?? 'configured'}-minute quiet period.`;
    case 'error':
      return `Project-field change detection failed: ${result.error || 'unknown error'}.`;
    default:
      return 'See the combined machine-readable decision block.';
  }
}

function projectSectionMarkdown(result, config) {
  const timeZone = config.summaryTimezone;
  let markdown = '\n### Project field synchronization\n\n';
  markdown += `**${projectDecisionLabel(result)} · ${projectActionLabel(result)}**\n\n`;
  markdown += `- **Workflow:** ${result.workflow || config.projectFieldSync?.workflow || '—'}\n`;
  markdown += `- **Issues:** ${issueLabel(result.issueNumbers)}\n`;
  markdown += `- **Watermark:** ${formatTimestamp(result.since, timeZone)}\n`;
  markdown += `- **Pending since:** ${formatTimestamp(result.pendingSince, timeZone)}\n`;
  markdown += `- **Latest Issue update:** ${formatTimestamp(result.latestUpdateAt, timeZone)}\n`;
  markdown += `- **Reason:** ${projectReason(result, timeZone, config)}\n`;
  return markdown;
}

function buildCombinedSummaryMarkdown(results, projectFieldResult, now, config) {
  if (!Array.isArray(results)) throw new Error('Scheduler summary results must be an array');
  if (!projectFieldResult || projectFieldResult.id !== 'project-fields') {
    throw new Error('Combined scheduler summary requires the project-fields decision');
  }

  const baseMarkdown = runtime.buildSummaryMarkdown(results, now, config);
  const markerIndex = baseMarkdown.lastIndexOf(MACHINE_MARKER);
  if (markerIndex < 0) throw new Error('Scheduler summary machine-readable marker changed unexpectedly');

  // Reuse the runtime's established target formatter and replace only its machine-readable tail.
  // Duplicating the normal target table here would create two observability formats that can drift.
  const humanPrefix = baseMarkdown.slice(0, markerIndex);
  const combinedResults = [...results, projectFieldResult];
  return `${humanPrefix}${projectSectionMarkdown(projectFieldResult, config)}${MACHINE_MARKER}${JSON.stringify(combinedResults, null, 2)}\n${MACHINE_SUFFIX}`;
}

async function writeCombinedSummary(core, results, projectFieldResult, now, config) {
  if (!core.summary || typeof core.summary.addRaw !== 'function') return false;
  const markdown = buildCombinedSummaryMarkdown(results, projectFieldResult, now, config);
  await core.summary.addRaw(markdown).write({ overwrite: true });
  return true;
}

module.exports = {
  buildCombinedSummaryMarkdown,
  projectActionLabel,
  projectDecisionLabel,
  projectReason,
  projectSectionMarkdown,
  writeCombinedSummary,
};
