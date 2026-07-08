# Repository History Hygiene Report

Date: 2026-07-03

## Commands

```bash
git log --all -- .env
git log --all -- node_modules
git log --all -- '*.sqlite3'
git log --all -- '*secret*'
git ls-files .env node_modules '*.sqlite3' '*secret*'
```

## Results

- `.env`: no history entries found.
- `*.sqlite3`: no history entries found.
- `node_modules`: history entries found. Playwright-related dependencies were committed in older commits and later removed.
  - `a83b4f6f Add node_modules and venv311`
  - `2a41d659 chore(repo): 生成ファイルをgit管理から除外`
  - `6ed74d6f 公開前の安全性チェックを強化`
- `*secret*`: entries are normal source/test files for secret handout behavior, not secret key material.
  - `accounts/migrations/0049_character_secret_ho_background_pdf_fields.py`
  - `tests/e2e/flows/secret-handout-flow.spec.ts`
- Currently tracked matching paths:
  - `accounts/migrations/0049_character_secret_ho_background_pdf_fields.py`
  - `tests/e2e/flows/secret-handout-flow.spec.ts`

## Recommendation

Before making the repository public, remove historical `node_modules` content with `git filter-repo` or an equivalent history rewrite, then force-push the cleaned repository if collaborators agree.

Suggested command pattern:

```bash
git filter-repo --path node_modules --invert-paths
```

After rewriting history, rerun the commands above and ask all collaborators to re-clone or reset to the rewritten history.