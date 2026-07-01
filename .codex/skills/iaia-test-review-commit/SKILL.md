---
name: iaia-test-review-commit
description: IAIA/Tableno repository workflow for testing, source reviewing, and committing local code changes. Use when the user asks Codex to test changes, run a source review, verify UI locally, prepare a commit, create one or more commits, or perform a combined "テスト・レビュー・コミット" pass in this Django/Bootstrap/JavaScript project.
---

# IAIA Test Review Commit

## Purpose

Use this skill to finish IAIA code changes with a disciplined test, source review, and commit workflow. Keep unrelated dirty worktree changes out of the review and commit.

## Workflow

1. Inspect the current state:
   - Run `git status --short`.
   - Run `git diff --name-only` and, when commits are involved, `git diff --stat`.
   - Identify files that are part of the requested work and files that appear unrelated.
   - Do not revert or stage unrelated user changes.

2. Read required local guidance:
   - Read `AGENTS.md` if it is present or supplied in the conversation.
   - For character sheet work, read relevant files under `docs/guidelines/` such as:
     - `CHARACTER_SHEET_GUIDELINES.md`
     - `JAVASCRIPT_GUIDELINES.md`
     - `UI_REFACTORING_GUIDELINES.md`
     - `TDD_GUIDELINES.md`
   - Load only the guidelines relevant to the touched files.

3. Run targeted tests before review:
   - Always run `git diff --check -- <intended files>`.
   - For JavaScript edits, run `node --check <changed-js-file>`.
   - For Django model/view/API/form changes, run the smallest relevant `python manage.py test ...` target first, then broaden if shared behavior changed.
   - For UI/template/CSS changes, run related static/unit UI tests and use the local browser when requested or when visual regressions are plausible.
   - For frontend work that needs a server, use the `iaia-local-server` skill to start or reuse `http://127.0.0.1:8000/`.

4. Perform source review before committing:
   - Review the actual diff, not only the final behavior.
   - Use a code-review stance: bugs, regressions, permission/security risks, data loss, missing tests, and UI accessibility/contrast issues first.
   - Verify user-facing behavior against the request.
   - If review finds issues, fix them and rerun the affected tests before committing.
   - If no actionable issues remain, say that explicitly.

5. Commit only after tests and review are clean:
   - Stage only intended files: `git add -- <file1> <file2> ...`.
   - Inspect `git diff --cached --stat` and, when necessary, `git diff --cached`.
   - Use a concise commit message that describes the user-visible change.
   - If the user asked for multiple commits, split by logical scope and verify each staged set.
   - Never include unrelated files such as environment settings, generated local state, or user work unless the user explicitly requested them.

6. Final response:
   - State what was tested and the outcome.
   - State the source review result.
   - State the commit hash or explain why no commit was created.
   - Mention unrelated dirty files that remain, if any.

## Test Selection Guide

- Character image/API changes:
  - `python manage.py test accounts.test_character_multiple_images accounts.test_character_image_apis -v 2`
- Character create/detail UI static behavior:
  - `python manage.py test tests.unit.test_character_create_ui_static -v 2`
- Production settings changes:
  - `python manage.py test tests.unit.test_production_settings -v 2`
- General syntax/whitespace:
  - `git diff --check -- <intended files>`
  - `node --check static/accounts/js/<file>.js`

Prefer targeted tests first. Broaden to app-level or full-suite tests only when the diff touches shared infrastructure, settings, authentication, permissions, or widely used frontend assets.

## Local Browser Check

When the user asks for local screen testing or the change affects responsive layout, modals, image display, navigation, contrast, or JavaScript interaction:

1. Use `iaia-local-server` to check/start the server.
2. Use the browser skill to inspect the page.
3. Create disposable local test data if needed, clearly scoped by a unique prefix.
4. Remove disposable data after verification.
5. Capture screenshots for UI verification and include important ones in the final response when the user asked for screen confirmation.
6. Check browser console errors after interacting with the changed UI.

## Commit Safety Rules

- Do not run `git reset --hard`, `git checkout --`, or destructive cleanup commands for unrelated changes.
- Do not stage all files with `git add .` when unrelated changes exist.
- Do not commit if tests fail unless the user explicitly asks for a failing checkpoint commit.
- Do not commit secrets, local env files, large generated artifacts, screenshots, or temp files unless explicitly requested and appropriate.
- If a requested commit would mix unrelated changes, stop and report the exact files that need user direction.
