# Safe Share Links and Legacy Import Specification

Last updated: 2026-06-27

This document is the current specification for safe external sharing and legacy Tableno data import. It supersedes older notes that describe only `private/public` visibility or session-only `share_token` sharing.

## Visibility Scopes

`private`, `group`, `link`, and `public` are distinct.

- `private`: visible only to the owner or users with management permission.
- `group`: visible according to group membership and group permissions.
- `link`: not visible through public listing or public ID URLs. It is readable only through a valid `ShareLink` URL.
- `public`: readable through public URL/API. A `ShareLink` can also be issued for public resources.

Supported resources:

- `CharacterSheet.access_scope`: `private`, `group`, `link`, `public`.
- `TRPGSession.visibility`: `private`, `group`, `link`, `public`.
- `Scenario.visibility`: `private`, `group`, `link`, `public`.

Legacy compatibility:

- `CharacterSheet.is_public` is legacy compatibility state. Current public-read checks use `access_scope`.
- `TRPGSession.share_token` remains a legacy public-session URL token and only works for `visibility='public'`.

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

Shared read endpoints:

- `GET /share/sessions/{token}/`
- `GET /share/characters/{token}/`
- `GET /share/scenarios/{token}/`
- `GET /share/stats/{token}/`

## Shared Response Safety

Shared serializers are intentionally separate from normal owner/member serializers.

Session sharing must not include:

- secret handouts
- participant email addresses
- user IDs
- OAuth or claim information
- admin-only fields

For legacy imported sessions, `gm_name` should prefer the GM `SessionParticipant.participant_identity.display_name`. `session.gm` is an internal management owner in CSV imports and is not necessarily the public GM display name.

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

Stats sharing returns display-name based aggregate and participant rows only.

## Legacy CSV Import

The management command `import_trpg_schedule` supports three source modes:

- `--excel-path`
- `--input-json`
- `--sessions-csv`

CSV mode is for past-session records that must be viewable and usable for stats without linking participants to login accounts.

CSV arguments:

- `--sessions-csv`: required for CSV mode.
- `--participants-csv`: optional participant rows.
- `--aliases-csv`: optional identity aliases.
- `--dry-run`: validate and count without writing.
- `--allow-duplicates`: import even when duplicate CSV rows are detected.
- `--group-name`: target group.
- `--default-gm-username`: internal owner user for created sessions.

CSV columns:

sessions:

```csv
legacy_session_id,title,date,duration_minutes,scenario_title,gm_name,visibility
```

participants:

```csv
legacy_session_id,participant_name,role,character_name,character_sheet_url
```

aliases:

```csv
identity_key,display_name,alias,memo
```

Import behavior:

- Participants are stored as `ParticipantIdentity` and `ParticipantIdentityAlias`.
- CSV participant rows are not resolved to `CustomUser`.
- CSV participant rows are not claimable through this import path.
- GM participant rows may be name-only when they have a `ParticipantIdentity`.
- `session.gm` is an internal owner for management and permissions.
- `legacy_session_id` is recorded in the session description for traceability.
- `duration_minutes`, `scenario_title`, and `visibility` are imported when provided.
- `visibility` defaults to `group` if blank or invalid.

Duplicate handling:

- Dry-run reports duplicate session IDs, participant rows, and alias rows.
- Real import aborts on duplicates unless `--allow-duplicates` is passed.
- Import runs in a transaction; failures roll back database writes.

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
