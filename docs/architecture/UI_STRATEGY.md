# UI Strategy — Functional Now, Demo POS Later

## Purpose
This document defines UI layering strategy for the current implementation window.

## Two UI Levels

### A) Functional Operator UI (admin-app)
Current priority is operator reliability and invariant visibility:
- visit-centric workflows,
- lock state visibility,
- explicit manual intervention actions,
- alignment with backend operational state.

This layer is intentionally pragmatic and does not aim to be final POS design.

### B) Demo POS UI (future)
A dedicated demo/presentation POS UI will be implemented in a later stage.
It will focus on polished interaction design and demo narrative after core operational milestones stabilize.

## Why we are not building the ideal design now
- Current milestones prioritize correctness of operational behavior.
- Backend invariants and offline/shift semantics are still evolving through M4–M6.
- A premature visual redesign would increase rework and dilute delivery focus.

## Backend-first reflection principle
UI must mirror backend invariants, not invent parallel client-side state logic.
For visit workflows this means:
- one active search entry point,
- visit as primary context,
- active tap lock state always explicit,
- manual actions mapped directly to backend transitions.

## Forward impact (M4–M6)
Upcoming milestones (offline sync handling, shift authority, security hardening) will affect UX flows.
Therefore, current UI should remain lean and adaptable while preserving clear functional hierarchy.
