from collections import defaultdict

from . import identity_v2 as _impl


def _build_components(candidates):
    uf = _impl.UnionFind()
    for _ in candidates:
        uf.add()

    existing_owner = {}
    anchor_owners = defaultdict(list)
    for idx, candidate in enumerate(candidates):
        if candidate.existing_internal_id:
            previous = existing_owner.get(candidate.existing_internal_id)
            if previous is not None:
                uf.union(idx, previous)
            else:
                existing_owner[candidate.existing_internal_id] = idx
        for key in _impl.ANCHOR_ID_KEYS:
            value = candidate.ids.get(key)
            if not value:
                continue
            token = (key, value)
            for previous in anchor_owners[token]:
                if _impl._can_merge_on_anchor(candidate, candidates[previous], key):
                    uf.union(idx, previous)
            anchor_owners[token].append(idx)

    # Provider-only current rows prefer current anchored evidence. Historical
    # canonical mappings are a fallback only when no current stable component
    # claims that provider ID. This preserves stable existing identities while
    # allowing a later provider-ID reuse to attach to the new current person.
    for _ in range(3):
        components = _impl._component_members(uf, candidates)
        stable_roots = {
            root
            for root, indexes in components.items()
            if _impl._component_is_stable(indexes, candidates)
        }
        current_token_roots = defaultdict(set)
        historical_token_roots = defaultdict(set)
        for idx, candidate in enumerate(candidates):
            root = uf.find(idx)
            if root not in stable_roots:
                continue
            target_map = (
                historical_token_roots
                if candidate.source == "canonical-existing"
                else current_token_roots
            )
            for key in _impl.ATTACH_ID_KEYS:
                if value := candidate.ids.get(key):
                    target_map[(key, value)].add(root)

        changed = False
        for idx, candidate in enumerate(candidates):
            root = uf.find(idx)
            if root in stable_roots:
                continue
            current_targets = set()
            historical_targets = set()
            for key in _impl.ATTACH_ID_KEYS:
                if value := candidate.ids.get(key):
                    current_targets.update(current_token_roots.get((key, value), set()))
                    historical_targets.update(historical_token_roots.get((key, value), set()))

            if len(current_targets) == 1:
                target = next(iter(current_targets))
            elif len(current_targets) == 0 and len(historical_targets) == 1:
                target = next(iter(historical_targets))
            else:
                continue

            target_indexes = components.get(target, [])
            if not _impl._component_compatible(candidate, target_indexes, candidates):
                continue
            uf.union(idx, target)
            changed = True
        if not changed:
            break

    # Remaining current app rows are allowed to establish provisional person
    # components because Sleeper is the current app identity contract. A single
    # otherwise-unanchored provider row may then attach to exactly one such app
    # component. Multiple rows claiming the same app mapping remain separate so
    # the later mapping-conflict audit quarantines the ambiguity instead of
    # silently collapsing them.
    components = _impl._component_members(uf, candidates)
    app_token_roots = defaultdict(set)
    for idx, candidate in enumerate(candidates):
        if candidate.source != "app.Players":
            continue
        root = uf.find(idx)
        for key in _impl.ATTACH_ID_KEYS:
            if value := candidate.ids.get(key):
                app_token_roots[(key, value)].add(root)

    proposals = defaultdict(list)
    for idx, candidate in enumerate(candidates):
        if candidate.source in {"app.Players", "canonical-existing"}:
            continue
        if _impl._component_is_stable(components.get(uf.find(idx), []), candidates):
            continue
        targets = set()
        for key in _impl.ATTACH_ID_KEYS:
            if value := candidate.ids.get(key):
                targets.update(app_token_roots.get((key, value), set()))
        if len(targets) == 1:
            proposals[next(iter(targets))].append(idx)

    for target, proposed_indexes in proposals.items():
        if len(proposed_indexes) != 1:
            continue
        idx = proposed_indexes[0]
        target_indexes = components.get(target, [])
        if _impl._component_compatible(candidates[idx], target_indexes, candidates):
            uf.union(idx, target)
    return uf


_impl._build_components = _build_components

from .identity_v2 import *  # noqa: E402,F401,F403
