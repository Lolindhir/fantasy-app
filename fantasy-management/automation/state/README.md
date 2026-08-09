# Fantasy Operations State

This directory contains durable Fantasy Operations state.

## Canonical human-approved observation baseline

`human-approved-observation-baselines.json` is the canonical machine-readable baseline for qualitative player observations that were researched externally, shown to Robert, and explicitly approved for persistence in an interactive chat.

Use this file when scheduled or interactive Fantasy Operations monitoring compares a newly researched player state with the last confirmed qualitative repository baseline.

Rules:

- A new or changed baseline may be written only after Robert explicitly approves the proposed observation in an interactive chat.
- Scheduled monitoring is read-only and must never update this file autonomously.
- The baseline records what was confirmed at a point in time; it is not permanent player truth.
- Fresh research still wins for current injury, availability, NFL roster status, role and opportunity conclusions.
- An unchanged current state matching an approved baseline must not be reported again merely because it is rediscovered.
- A material change from an approved baseline may trigger a notification; persistence of the changed state again requires explicit approval.
- Generated datasets under `fantasy-management/generated/**` remain reproducible neutral working data and must not contain these human-approved qualitative observations.

## Legacy observation state

`entity-observation.json` belongs to the former autonomous observation runner. It is retained as historical/migration state. The legacy runner must remain read-only and must not autonomously publish State.

New provider-neutral monitoring should use `human-approved-observation-baselines.json` for approved qualitative baselines instead of extending the autonomous bootstrap/replacement-state mechanism.
