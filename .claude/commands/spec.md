# /spec — Generate an Implementation Spec for a Cheaper Model

You are the architect of NetSim-Flow. When this command is invoked you produce a self-contained implementation spec file that a less capable model (e.g. Claude Haiku) can follow without needing any other context.

## What to build

The user's request: $ARGUMENTS

---

## Your process (follow every step in order)

### Step 1 — Understand the request

Parse $ARGUMENTS and identify:
- What feature, fix, or task is being requested?
- Which layer(s) does it touch? (frontend canvas / frontend hooks / frontend store / API router / API service / API engine / shared types / tests)
- Does it touch existing files or require new ones?

If $ARGUMENTS is empty or ambiguous, ask the user ONE clarifying question before proceeding.

### Step 2 — Read before you write

Read every file that the implementing agent will need to touch or reference. Do not skip this step. Use the Read and Grep tools. Look at:
- The files the spec will say to modify
- One existing file of the same type (as a pattern example)
- The relevant shared types if the task touches data structures

### Step 3 — Determine the spec file name and branch

- Spec slug: short kebab-case description of the task, e.g. `password-reset-endpoint`
- Spec file: `specs/SPEC-<slug>.md`
- Suggested branch: `feat/<slug>` or `fix/<slug>`

Create the `specs/` directory at the repo root if it does not exist.

### Step 4 — Write the spec file

Write the spec to `specs/SPEC-<slug>.md`. The spec must follow this exact template:

---

```markdown
# Spec: <Title>

**Branch:** `<feat|fix|chore>/<slug>`
**Spec file:** `specs/SPEC-<slug>.md`
**Status:** ready-for-implementation

---

## Goal

One paragraph. What this task accomplishes and why. No implementation details yet.

---

## Scope

**In scope:**
- Bullet list of exactly what will be built

**Out of scope (do not implement):**
- Bullet list of things that might seem related but are explicitly excluded

---

## Files to Read First

Before writing any code, read these files to understand the existing patterns:

| File | Why |
|------|-----|
| `path/to/file.ts` | Pattern for X |
| `path/to/file.py` | Pattern for Y |

---

## Implementation Steps

Complete these steps in order. Do not skip steps. Do not combine steps.

### Step 1 — <verb> <what>

**File:** `exact/path/to/file.ts` *(create | modify)*

<For a new file: show the complete file content or a complete skeleton with TODO markers only where business logic must be filled in.>

<For a modification: show the exact location (function name + line context) and the exact change to make. Use before/after blocks:>

Before:
```language
<exact existing code to replace>
```

After:
```language
<exact new code>
```

### Step 2 — <verb> <what>

*(repeat for each step)*

---

## Tests to Add or Update

For each test, specify:
- **File:** exact path
- **Test name:** exact string for `it(...)` or `def test_...`
- **What it asserts:** one sentence

---

## Validation Commands

Run these in order after implementation. All must pass before the task is done.

```powershell
# 1. Type check (frontend)
cd apps/frontend && pnpm tsc --noEmit

# 2. Lint
turbo lint

# 3. Backend tests
cd apps/api && pytest tests/unit/test_<relevant>.py -v

# 4. Frontend tests
cd apps/frontend && pnpm test

# 5. Manual check (if applicable)
# <describe what to open in browser and what to verify>
```

---

## Architectural Checklist

The implementing agent must verify each item before marking the task done:

- [ ] No HTTP calls to GNS3 outside `apps/api/app/engines/`
- [ ] No `@xyflow/react` imports outside `apps/frontend/src/canvas/`
- [ ] No business logic in router functions
- [ ] No API calls directly in React components
- [ ] All new public Python functions have type hints
- [ ] All new Pydantic schemas are suffixed `Schema`
- [ ] Shared types updated and rebuilt if the data contract changed
- [ ] Every new service function has at least one unit test
- [ ] Every new API route has at least one integration test
- [ ] No `console.log` or `print()` debug statements
```

---

### Step 5 — Summarize for the user

After saving the spec file, tell the user:
1. The spec file path: `specs/SPEC-<slug>.md`
2. The suggested branch name
3. A 3-bullet summary of what the implementing agent will do
4. The exact command to run in a Haiku session to start implementation:
   ```
   Read the file specs/SPEC-<slug>.md completely, then implement every step in order.
   ```
