# Issue tracker: GitHub

Issues and specs live in GitHub. Use `gh` for every issue or pull-request operation; it infers the repository from the current clone.

## Issue workflow

1. **Create:** `gh issue create --title "..." --body "..."`. Done when the command returns an issue number.
2. **Read:** `gh issue view <number> --comments`; inspect labels and filter comments with `jq` when needed. Done when title, body, labels, and relevant comments are available.
3. **List:** `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`, adding appropriate `--label` and `--state` filters. Done when results are narrowed to actionable issues.
4. **Comment:** `gh issue comment <number> --body "..."`. Done when the comment is recorded.
5. **Label:** `gh issue edit <number> --add-label "..."` or `--remove-label "..."`. Done when the intended label state is visible.
6. **Close:** `gh issue close <number> --comment "..."`. Done when the issue is closed with resolution context.

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs use the same labels and states as issues through `gh pr` equivalents:

- **Read:** `gh pr view <number> --comments` and `gh pr diff <number>`.
- **List external PRs:** `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments`, retaining `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR`, or `NONE` author associations and dropping `OWNER`, `MEMBER`, and `COLLABORATOR`.
- **Comment, label, or close:** use the corresponding `gh pr` command.

GitHub shares one number space across issues and PRs. Resolve a bare `#42` with `gh pr view 42`, then fall back to `gh issue view 42`.

## Shared routing

- “publish to the issue tracker” means create a GitHub issue.
- “fetch the relevant ticket” means run `gh issue view <number> --comments`.

## Wayfinding operations

Used by `/wayfinder`. The **map** is one issue with child issues as tickets.

- **Map:** create one issue labelled `wayfinder:map` with Notes, Decisions-so-far, and Fog.
- **Child ticket:** link it to the map as a GitHub sub-issue with `gh api`. If sub-issues are unavailable, add it to the map task list and put `Part of #<map>` at the top. Use `wayfinder:<type>` labels (`research`, `prototype`, `grilling`, `task`). Assign the driving developer after claiming.
- **Blocking:** use GitHub native issue dependencies. Add an edge with `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where `<blocker-db-id>` is the blocker's numeric database id from `gh api repos/<owner>/<repo>/issues/<n> --jq .id`. If unavailable, put `Blocked by: #<n>, #<n>` at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Frontier:** list open map children, remove tickets with an open blocker or assignee, and choose the first remaining ticket in map order.
- **Claim:** `gh issue edit <n> --add-assignee @me`; this is the session's first write.
- **Resolve:** comment with `gh issue comment <n> --body "<answer>"`, close with `gh issue close <n>`, then append a context pointer (gist + link) to Decisions-so-far. Done when all three records exist.
