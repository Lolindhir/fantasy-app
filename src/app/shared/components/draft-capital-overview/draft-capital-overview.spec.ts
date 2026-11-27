import type { League, FantasyTeam } from '../../../core/models/league.models';
import type { RawDraft, DraftPick } from '../../../core/models/draft.models';
import { DraftCapitalOverviewComponent } from './draft-capital-overview';

describe('DraftCapitalOverviewComponent inputs', () => {
  it('uses the parent draft and team objects, recomputes on input change and hides other phases', () => {
    const draft = { DraftKey: '2026-rookie', Season: '2026', DraftNo: 1, DisplayDraftType: 'Rookie', DisplayDraftKey: 'Rookie' } as RawDraft;
    const pick = {
      DraftKey: draft.DraftKey, Season: '2026', Round: 1, DisplayPick: '1.01',
      Status: 'Open', SleeperPickNo: null, Draft: draft
    } as DraftPick;
    const team = { TeamID: 1, Team: 'Example', TeamAbbr: 'EX', DraftPicks: [pick] } as unknown as FantasyTeam;
    const component = new DraftCapitalOverviewComponent();
    component.league = { Season: '2026', Status: 'Off-Season', Teams: [team] } as unknown as League;
    component.drafts = [draft];
    component.ngOnChanges();
    expect(component.vm?.rows[0].team).toBe(team);
    expect(component.vm?.rows[0].draftCounts[0].count).toBe(1);
    expect(component.vm?.showSecondBestPick).toBeTrue();
    component.drafts = [];
    component.ngOnChanges();
    expect(component.vm).toBeNull();
    component.drafts = [draft];
    component.league = { ...component.league, Status: 'In-Season' };
    component.ngOnChanges();
    expect(component.vm).toBeNull();
  });
});
