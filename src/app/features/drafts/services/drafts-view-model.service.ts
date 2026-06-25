import { Injectable } from '@angular/core';
import type { FantasyTeam, League, Player, RawDraft } from '../../../core/models/fantasy.models';
import type { DraftsViewModel, DraftViewModel } from '../models/drafts-view.models';
import {
  createDraftsViewModel as createDraftsViewModelFromData,
  createDraftViewModels as createDraftViewModelsFromData
} from '../utils/drafts-view-model.mapper';

@Injectable({
  providedIn: 'root'
})
export class DraftsViewModelService {
  createDraftsViewModel(
    league: League,
    drafts: RawDraft[],
    teams: FantasyTeam[],
    players: Player[] = []
  ): DraftsViewModel {
    return createDraftsViewModelFromData(league, drafts, teams, players);
  }

  createDraftViewModels(
    drafts: RawDraft[],
    teams: FantasyTeam[],
    players: Player[] = []
  ): DraftViewModel[] {
    return createDraftViewModelsFromData(drafts, teams, players);
  }
}
