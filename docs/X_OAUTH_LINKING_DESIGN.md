# X OAuth + Manual Linking Design

## Goals
- Allow X-only login without requiring an email address.
- Keep a single user identity across Google, X, and email/password via manual linking.
- Use OAuth2 + PKCE for mobile and API-based login.
- Avoid auto-linking; require the user to link accounts after login.

## Non-Goals
- Automatic account merge by email.
- Passwordless email login.

## Login Flows

### X Login (Mobile/API)
1. App starts OAuth2 + PKCE with X.
2. App sends `code` + `code_verifier` to `POST /api/auth/twitter/`.
3. Server exchanges code for access token, fetches `users/me`.
4. If a SocialAccount exists, log in that user.
5. If not, create a new user and SocialAccount.

### X Login (Web)
1. User clicks X login button on `/login/`.
2. django-allauth handles the OAuth flow and creates SocialAccount.

### Manual Linking (Web)
1. User logs in with any method.
2. User opens `/accounts/social/connections/` from profile.
3. User links Google/X or adds email login.

### Manual Linking (API)
- If the user is authenticated and calls `POST /api/auth/twitter/`, the X account is linked to the current user.
- If the X account is already linked to a different user, return a conflict error.

## Settings
- Enable provider: `allauth.socialaccount.providers.twitter`
- Allow social signup without email:
  - `ACCOUNT_EMAIL_REQUIRED = False`
  - `SOCIALACCOUNT_EMAIL_REQUIRED = False`
- X OAuth API config:
  - `X_CLIENT_ID`
  - `X_CLIENT_SECRET` (optional for PKCE)
  - `X_REDIRECT_URI`

## API Endpoints
- `POST /api/auth/twitter/`
  - Request: `code`, `code_verifier`, optional `redirect_uri`
  - Response: DRF token + user + `linked` flag

## Data Model
- `SocialAccount` (provider: `twitter`, uid: X user id)
- `CustomUser` with optional `email`

## UI Changes
- Login page shows X button when SocialApp is configured.
- Connections page lists X and allows manual linking/unlinking.

## Security Notes
- Use OAuth2 + PKCE for mobile.
- Do not auto-link by email to avoid account takeovers.
- Block linking if X account is already attached to a different user.
