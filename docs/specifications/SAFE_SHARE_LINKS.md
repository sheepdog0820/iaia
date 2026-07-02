# Safe Share Links Specification

Last updated: 2026-07-02

This document describes the current external sharing behavior. Legacy public ID URLs and legacy CSV import mode have been removed.

## Visibility Scopes

`private`, `group`, `link`, and `public` are distinct.

- `private`: visible only to the owner or users with explicit permission.
- `group`: visible according to group membership and group permissions.
- `link`: readable only through a fixed share URL or an issued `ShareLink` URL.
- `public`: readable through the same share surfaces and may be listed where public listing exists.

Supported resources:

- `CharacterSheet.access_scope`: `private`, `group`, `link`, `public`.
- `TRPGSession.visibility`: `private`, `group`, `link`, `public`.
- `Scenario.visibility`: `private`, `group`, `link`, `public`.

## Share URLs

Fixed page URLs:

- `GET /share/characters/{share_token}/view/`
- `GET /share/sessions/{share_token}/view/`
- `GET /share/scenarios/{share_token}/view/`

Shared JSON URLs:

- `GET /share/characters/{token}/`
- `GET /share/sessions/{token}/`
- `GET /share/scenarios/{token}/`
- `GET /share/stats/{token}/`

Character helper endpoints:

- `GET /share/characters/{token}/ccfolia.json`
- `GET /share/characters/{token}/images/`
- `GET /share/characters/{token}/images.zip`

Old public ID routes are intentionally not available. Link-only resources must not be readable by integer primary key.

## ShareLink

`ShareLink` stores resource-level share URLs without storing raw tokens.

Fields:

- `resource_type`: `character`, `session`, `scenario`, or `profile_stats`.
- `object_id`: target object primary key.
- `token_digest`: SHA-256 digest of the raw token.
- `created_by`: issuing user.
- `expires_at`: optional expiry.
- `revoked_at`: revocation timestamp.
- `allow_anonymous`: whether unauthenticated access is allowed.
- `view_level`: `summary`, `standard`, or `full`.
- `created_at`: issue timestamp.

Rules:

- Raw tokens are returned only on issue/reissue.
- A share URL can be issued only by the resource owner or manager.
- The target resource must be `link` or `public`.
- Revoked or expired links return 404.
- If `allow_anonymous=false`, anonymous requests return 404.

Management endpoints:

- `GET /api/share-links/`
- `POST /api/share-links/`
- `POST /api/share-links/{id}/revoke/`
- `POST /api/share-links/{id}/reissue/`
- `POST /api/share-links/fixed-url/`

## Shared Response Safety

Shared serializers are intentionally separate from normal owner/member serializers.

Session sharing must not include:

- secret handouts
- participant email addresses
- user IDs
- OAuth or claim information
- admin-only fields

Character sharing must not include:

- owner or allowed-user information
- private notes
- version notes
- internal access-control fields beyond safe display scope

Scenario sharing must not include:

- GM notes
- secret scenario handouts
- creator private fields

Stats sharing must not include:

- user IDs
- email addresses
- claim or login linkage

## Data Import

`import_trpg_schedule` supports current Excel/JSON import only:

- `--excel-path`
- `--input-json`

The import creates sessions, participants, scenarios, and YouTube links from the prepared schedule payload. Name-only historical CSV import was removed before public release.

## Verification

Core tests:

- `accounts.test_share_links`
- `tests.unit.test_import_trpg_schedule`
- `scenarios.test_scenarios`
- `schedules.test_schedules.PublicSessionLinkTestCase`
- `schedules.test_session_visibility`

Representative command:

```bash
python manage.py test accounts.test_share_links tests.unit.test_import_trpg_schedule scenarios.test_scenarios schedules.test_schedules.PublicSessionLinkTestCase schedules.test_session_visibility -v 2
python manage.py check
```
