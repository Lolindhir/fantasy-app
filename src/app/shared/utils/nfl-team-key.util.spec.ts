import { canonicalNflTeamKey, findNflTeam, nflTeamKeysMatch } from './nfl-team-key.util';

describe('nfl-team-key util', () => {
  const nflTeams = [
    { ID: 'AAA', LegacyIDs: ['7'] },
    { ID: 'BBB', LegacyIDs: ['12', 'OLD'] },
    { ID: '31' }
  ];

  it('finds a team by current ID or legacy ID, ignoring case and whitespace', () => {
    expect(findNflTeam(nflTeams, 'aaa')?.ID).toBe('AAA');
    expect(findNflTeam(nflTeams, ' 7 ')?.ID).toBe('AAA');
    expect(findNflTeam(nflTeams, 12)?.ID).toBe('BBB');
    expect(findNflTeam(nflTeams, 'old')?.ID).toBe('BBB');
  });

  it('prefers a current ID over a legacy ID and tolerates teams without LegacyIDs', () => {
    expect(findNflTeam(nflTeams, '31')?.ID).toBe('31');
  });

  it('returns null for unknown or empty references', () => {
    expect(findNflTeam(nflTeams, 'ZZZ')).toBeNull();
    expect(findNflTeam(nflTeams, '')).toBeNull();
    expect(findNflTeam(nflTeams, null)).toBeNull();
    expect(findNflTeam([], '7')).toBeNull();
  });

  it('canonicalizes known references and keeps unknown ones unchanged', () => {
    expect(canonicalNflTeamKey(nflTeams, '7')).toBe('AAA');
    expect(canonicalNflTeamKey(nflTeams, ' ZZZ ')).toBe('ZZZ');
  });

  it('matches references to the same team across key forms only', () => {
    expect(nflTeamKeysMatch(nflTeams, '7', 'AAA')).toBeTrue();
    expect(nflTeamKeysMatch(nflTeams, 'OLD', '12')).toBeTrue();
    expect(nflTeamKeysMatch(nflTeams, 'AAA', 'BBB')).toBeFalse();
    expect(nflTeamKeysMatch(nflTeams, '', '')).toBeFalse();
    expect(nflTeamKeysMatch([], 'X', 'x')).toBeTrue();
  });
});
