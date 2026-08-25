# Chat Start

Repository: `Lolindhir/fantasy-app`

This file is a stable entry prompt for new chats. It should not duplicate detailed project rules.

## Stable rule

Before answering repo-specific questions, suggesting implementation changes or changing files:

1. Read the repository root `AGENTS.md` first.
2. Follow the context routing defined in `AGENTS.md`.
3. For application, frontend, data generation, generated JSON contract, routing or architecture work, use the application context files referenced by `AGENTS.md`.
4. For NFL Dynasty / Fantasy Management, Mighty Giants, StonedLack, Relevant Players, trades, roster, draft, free agents, player evaluations, boards, analyses or decisions, use `fantasy-management/AGENTS.md`.
5. Treat the repository instructions as canonical. Do not duplicate detailed rules in the chat-start prompt.
6. For repository work tracking, follow the GitHub Issue workflow and label semantics defined by the repository instructions and canonical work-tracking documentation.
7. Do not maintain parallel Markdown todo lists once the issue-based migration is complete.

## Short prompt for new chats

```text
Repo: Lolindhir/fantasy-app. Read the root AGENTS.md first and follow its context routing. Use the application .ai-context files for app/frontend/data-generation work, and use fantasy-management/AGENTS.md for NFL Dynasty / Fantasy Management work. Treat repo instructions as canonical instead of duplicating detailed rules in chat. For repository work tracking, follow the GitHub Issue workflow and canonical work-tracking documentation.
```
