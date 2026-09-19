# League Context

This folder stores Fantasy Management context that is specific to the user's dynasty league but is not generated app data.

Use this folder for:

- owner and team identity resolution
- user perspective and aliases
- league format interpretation
- manager tendencies
- trade negotiation history
- negotiation strategy notes

Productive current league state still comes from `public/data/League.json` and `public/data/Metadata.json` until the corresponding Canonical Source consumer cutover is explicitly completed. `owner-registry.json` additionally carries the explicit stable `TeamID -> CanonicalLeagueMemberID` identity bridge used by the Checkpoint-6P canonical ownership shadow; provider roster IDs are provenance only and must not be treated as stable TeamIDs.

Files in this folder are strategic or identity context. Re-check current generated data before dynamic roster, pick, salary, trade or standings conclusions; the 6P canonical ownership adapter is shadow/parity evidence only and does not yet replace the productive App readmodel.
