// Golden dump of the former Angular rivalry util (src/app/shared/utils/team-rivalry.util.ts at main before Issue #1455 cutover).
// Usage: node research/league-rivalry/2026/golden-ts-dump.mjs <repoRoot> <utilPath> > golden.json
// Needs Node 22+ (native type stripping); the util only has type imports.
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const [repo, utilPath] = process.argv.slice(2);
const util = await import(pathToFileURL(utilPath).href);
const read = path => JSON.parse(readFileSync(join(repo, path), 'utf8'));
const league = read('public/data/League.json');
const currentSeason = Number(league.Season);
const status = league.Status;
const seasons = [
  ...readdirSync(join(repo, 'public/data/past_seasons/Matchups')).sort().map(f => read(`public/data/past_seasons/Matchups/${f}`)),
  read('public/data/Matchups.json')
].filter((s, i, all) => all.findIndex(o => o.Season === s.Season) === i);
const teamIds = [...new Set(seasons.flatMap(s => s.Weeks.flatMap(w => w.Matchups.flatMap(m => m.Participants.map(p => p.TeamID)))))].sort((a, b) => a - b);
const out = [];
for (const filter of ['all', 'regular', 'playoffs']) {
  for (const teamId of teamIds) {
    const records = util.buildRivalryRecords(teamId, seasons, { filter, isSeasonComplete: s => util.isPlayoffsComplete(s, currentSeason, status) });
    for (const r of records) out.push({ TeamID: teamId, OpponentID: r.opponentId, Filter: filter, Wins: r.wins, Losses: r.losses, Ties: r.ties, PointsFor: r.pointsFor, PointsAgainst: r.pointsAgainst, Games: r.games });
  }
}
process.stdout.write(JSON.stringify(out));
