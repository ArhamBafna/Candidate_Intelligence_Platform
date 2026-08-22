# Anti-AI Pattern Findings (Whole UI Scan)

Files scanned: `ui/src/pages/CandidateList.jsx`, `ui/src/pages/CandidateDetail.jsx`, `ui/src/components/SystemLogDrawer.jsx`, `ui/src/index.css`, `ui/src/App.css`, `ui/index.html`, docs (`docs/**/*.md`, root README). Scan ran immediately after the deliberate black-theme recolor (#000 page, #0a0a0a cards, #171717 inputs, emerald accent).

## 1. Hallmark Audit

[critical] Card-in-card nesting — CandidateList.jsx:820, :903, :979, :1060, :1223
  Bordered panels stacked inside bordered panels with no semantic need; containment-layer tell.
  fix: one containment layer per surface — replace inner boxes with hairline dividers (`border-t border-neutral-800 pt-3`) or plain spacing; warnings become left-aligned lists.
  *Safety: CSS/markup only, low risk.*

[major] Sparkle-as-AI-badge — CandidateList.jsx:1070, 1086, 1118, 1292, 1313, 1343
  Sparkle glyph beside every AI label is the named cliché even from an icon library.
  fix: drop `Sparkle` import/usage; reuse existing markers (pulsing emerald dot at :823, uppercase "AI" chip at :912).
  *Safety: markup/CSS only.*

[major] Bounce easing on UI state — CandidateList.jsx:1118, 1343 (`animate-bounce`)
  Bouncing icons are an easing tell; house motion is `animate-pulse`.
  fix: remove `animate-bounce`; use `animate-pulse` or nothing.
  *Safety: CSS only, zero risk.*

[major] Shadow-glow halo on dark cards — CandidateList.jsx:638, :708
  Colored soft halos (`rgba(16,185,129,…)` glows) around dark surfaces are the shadow-glow tell; elevation should come from lightness steps.
  fix: delete glow shadows; selected state already reads via border + `ring-2`.
  *Safety: CSS only, zero risk.*

[major] Uniform equal-column SaaS card grid — CandidateList.jsx:698
  Three equal columns of identical card anatomy is the default LLM dashboard fingerprint.
  fix: vary rhythm — rank-1 result as full-width featured row, rest 2-col; or dense ranked-list using existing `rank`/`rrf_score` data.
  *Safety: layout change, medium functional risk (retest selection/menu/insight interactions).*

[major] `transition-all` — CandidateList.jsx:594, 638, 706
  Every-property animation incl. focus ring is a microinteraction tell.
  fix: `transition-colors`, or `transition-[border-color,box-shadow]`; never transition focus ring.
  *Safety: CSS only, zero risk.*

[major] Fabricated placeholder facts — CandidateList.jsx:427–429
  `|| 'Software Engineer'`, `|| 'Tech Corp'`, `|| 'Remote'` invent employer/title data for real candidates — UI states lies as fact.
  fix: fall back to `'—'` or omit the row.
  *Safety: display logic change, low functional risk.*

[major] Browser-native `alert()` dialogs — CandidateList.jsx:196, 200, 492, 496; CandidateDetail.jsx:171, 175
  Raw `alert()` for failures is generated-UI roughness; banned by repo rules.
  fix: inline error banner styled like the existing amber warning banner (:657).
  *Safety: functional risk — replaces error path; verify delete flows after.*

[minor] `.glass-panel` frosted-glass naming — index.css:47 (7 usages across both pages)
  Name promises glassmorphism (named tell); actual styles are solid neutral-950 + border.
  fix: rename to `.panel` / `.surface-panel`; styles unchanged.
  *Safety: CSS-rename only, zero visual risk.*

[minor] Dead misleading `.gradient-text` class — index.css:51
  Named like the gradient-headline anti-pattern, contains no gradient, referenced nowhere.
  fix: delete the class.
  *Safety: zero risk.*

[minor] Dead Vite scaffold stylesheet — App.css:1–184 (imported at App.jsx:5)
  `.hero`, `#center`, `#counter`, `#next-steps`, `.ticks` referenced by no JSX; template residue.
  fix: empty file (keep import) or remove import + file together.
  *Safety: zero risk (classes unused).*

[minor] Dead ternary — CandidateList.jsx:631 (`{isSearching ? 'Search' : 'Search'}`)
  Both branches identical — unproofread-generation sign.
  fix: render `'Search'`, or make branches real (`'Searching…'` + disabled).
  *Safety: trivial; verify submit guard if adding disabled state.*

[minor] Three periods instead of ellipsis — CandidateList.jsx:217, 385, 888, 937, 1046, 1099, 1265
  `...` in rendered copy is a listed proofread tell.
  fix: use `…` (U+2026) in user-visible strings.
  *Safety: copy only, zero risk.*

[minor] Arbitrary z-index values — CandidateList.jsx:881, 1001, 1038, 1162, 1211, 1257
  Magic z-numbers with no declared scale.
  fix: define tokens (`--z-bar: 50; --z-modal: 60; --z-confirm: 70`) in `:root`.
  *Safety: CSS only, zero risk.*

[user-decision] Pure black page surface — index.css:6, :38 (`bg-black`)
  Hallmark flags pure `#000000` as flat/synthetic, but this was the explicit user request ("dark mode which is black").
  fix: none required. Optional within intent: lift cards one more lightness step for stronger elevation contrast.
  *Safety: n/a.*

**Explicit passes:** single icon library (@phosphor-icons/react — not the Lucide-default trap); Outfit + Roboto two-face pairing (not Inter-everywhere); no purple/blue gradients remain after recolor.

Summary — 1 critical · 8 major · 6 minor · 1 user-decision
Verdict — reads as AI-generated

---

## 2. Design-Taste-Frontend Audit

- **Lila (purple/blue) trap**: cleared by this session's recolor — indigo/purple/slate-blue fully replaced with emerald + neutral black layers. Residual purple exists only in `ui/src/assets/hero.png` pixels; asset has **zero imports/references in any JSX** (dead weight, safe to delete later).
- **Default generic SaaS grid**: hit — see Hallmark [major] grid finding (CandidateList.jsx:698).
- **Inter-everywhere font**: pass — Outfit display + Roboto body via Google Fonts (index.css:1).

---

## 3. Impeccable Critique & Layout Structure

- **Heuristic Score**: 5.5/10 — solid operate-mode skeleton (consistent spacing/loading/empty/error states), but four collapsed surface layers on the new black theme, clone-stamped cards with dead score-tier logic, duplicated/dead controls.
- **Action**: distill pass guidance below.
  1. **Break card monotony** — fix dead match-tier conditional (CandidateList.jsx:742–743 renders byte-identical classes for ≥80 and ≥50 tiers); render the already-mapped-but-unused `rank` chip (:431–434); replace identical `<User>` avatar icons with initials monograms (:726–728).
     > ⚠️ **EXTRA CAREFUL (POTENTIAL FUNCTIONAL RISK):** whole card navigates via `onClick` (:705); any added interactive element must follow the existing `stopPropagation` chain (:47–52, :478–481, :764, :828, :835, :851) or it fires navigation and orphans running SSE reader loops (:101–166 insights, :519–554 reprocess).
  2. **Rebuild black-theme depth ladder** — page 0% vs card 4% luminance barely separates; raise `--card` toward ~#141414, strengthen `.glass-panel` border/hover, bump input fill one step (CandidateList.jsx:594, CandidateDetail.jsx:305).
     SystemLogDrawer.jsx: light-mode badge chips (:50–55) glare on dark drawer — restyle to `bg-red-500/10` convention; timestamp `#525252` on `#0a0a0a` ≈ 2.8:1 contrast fails WCAG (:233); raw `✕` glyph (:144); hardcoded hexes duplicating tokens (:97, :112).
  3. **One primary action per view** — identical emerald "Download Resume" rendered twice above fold (CandidateDetail.jsx:208–214 vs :272–291; quick-access card pushes profile data below scroll fold — delete card, keep header button). "View Profile" footer button has no `onClick` (CandidateList.jsx:861–865 — works only by bubbling; wire explicitly or remove). Dead ternary at :630–632. Pseudo-checkboxes lack semantics — add `role="checkbox"` + `aria-checked` to AI Notes (:620–629), Select All (:673–687), per-card select (:715–725).
     > ⚠️ **EXTRA CAREFUL (POTENTIAL FUNCTIONAL RISK):** reprocess/upload/batch modals are driven by open SSE reader loops writing state directly; Close buttons are deliberately guarded `disabled={status === 'IN_PROGRESS'}` (CandidateList.jsx:1053, :1273; CandidateDetail.jsx:433). A naive overlay/backdrop click-to-close bypasses the guard mid-stream, abandons the reader loop, and skips the wired `fetchCandidates()` refresh (:1049–1052, :1268–1272, :429–432). Same care for auto-save debounce (CandidateDetail.jsx:84–97): any input restructuring must keep the clearTimeout/setTimeout pair or saves silently stop.

---

## 4. Humanise-Text Review (docs + UI copy)

UI JSX (all audited files) and root README: zero fluff vocabulary — clean.

- **AI Pattern**: streamline (docs/tests/end-to-end/ui_test_report.md:37).
  fix: "speed up bulk batch actions". Same string is generated by `docs/tests/end-to-end/runner.js:342` — patch source too if accepted.
- **AI Pattern**: leverage (docs/ideas/architecture-deepening-opportunities.md:3).
  fix: "ordered by impact" (internal doc, optional).
- Internal-doc skips (technically accurate usage, no change): robust ×2 (docs/chats/trae-chat.md:108,140); harness = technical term (docs/task.md:15, docs/handoffs/handoff-performance-optimization.md:8); ensure/enhanced ×15 across trae-chat.md, async-ai-insights.md, ui_test_report.md.

---

## 5. Implementation Agent Prompt

> In `ui/src/` only, apply these fixes without changing behavior:
> 1. CandidateList.jsx: remove `Sparkle` import and all sparkle usages on AI badges (reuse pulsing dot / "AI" chip pattern); remove `animate-bounce`; delete the two colored glow shadows; replace `transition-all` with `transition-colors` or `transition-[border-color,box-shadow]`; replace fabricated fallbacks at :427–429 with `'—'`; fix dead ternary at :631; swap `...` → `…` in user-visible strings; add `role="checkbox"`+`aria-checked` to the three pseudo-checkbox toggles; give "View Profile" an explicit `onClick={() => navigate(...)}`; make match-tier badges visually distinct (≥80 solid emerald, 50–79 outline, <50 amber); render a small rank chip when `rank` exists.
> 2. Replace all six native `alert()` calls (CandidateList.jsx:196, 200, 492, 496; CandidateDetail.jsx:171, 175) with inline error banners styled like the amber banner at CandidateList.jsx:657. Keep error semantics identical.
> 3. index.css: rename `.glass-panel` → `.surface-panel` (update all 7 usages), delete `.gradient-text`, raise `--card` to ~`0 0% 8%`, define z-index tokens and use them.
> 4. SystemLogDrawer.jsx: restyle status chips to dark convention (`bg-red-500/10` style), brighten timestamp color to pass 4.5:1, replace `✕` glyph with a Phosphor icon, migrate remaining hardcoded hexes near token values.
> 5. Empty App.css body (keep the import) or remove import + file.
> 6. Do NOT touch: SSE reader loops, modal open/close guards, debounced save timer, stopPropagation chains, hero.png handling. After changes run `npm run build` and `npm run lint` in `ui/`.
