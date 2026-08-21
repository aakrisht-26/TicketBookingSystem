# 2. No version prefix on the API path

- Status: accepted
- Date: 2026-08-21

## Context

`CLAUDE.md` fixes the API prefix at `/api` and asks that a `/v1` segment be
justified in a record rather than added by reflex. The reflex is strong: most
public APIs carry one, so its absence looks like something forgotten unless the
reasoning is written down.

A version segment buys the ability to serve two incompatible contracts at once.
That is worth real money when clients are third parties on their own upgrade
schedules, because the provider cannot know when the last caller of the old
shape goes away.

None of that holds here. This API has exactly one client, the React frontend in
this repository, deployed from the same commit as the backend by the same
Render service. There is no window in which an old client talks to a new
server. The frontend's API client is generated from the backend's OpenAPI
schema and `tsc --noEmit` runs in CI, so an incompatible backend change breaks
the frontend build in the pull request that makes it. That is a stronger
guarantee than a version prefix provides, and it arrives sooner.

## Decision

Routes are mounted under `/api` with no version segment.

If this API ever gains a client that is not deployed with it, versioning is
introduced then, by mounting a second router under `/api/v2` and leaving the
unprefixed routes serving the original contract. Nothing about this decision
makes that harder later.

## Consequences

One less path segment in every route, one less thing to keep consistent, and no
directory named `v1` that would have to be either renamed or lived with.

The cost is that a genuinely breaking change has to be coordinated across
backend and frontend in one pull request. Given they are one deployment, that
coordination was required anyway; the version prefix would only have hidden it.

A reviewer expecting `/v1` finds this record, which is the point.
