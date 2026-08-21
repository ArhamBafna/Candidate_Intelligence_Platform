# Anti-AI Pattern Findings (Whole UI Scan)

Files scanned: `ui/src/pages/CandidateList.jsx`, `ui/src/pages/CandidateDetail.jsx`, `ui/src/components/SystemLogDrawer.jsx`, `ui/src/index.css`.

## 1. Hallmark Audit

[critical] The gradient headline — ui/src/pages/CandidateList.jsx:448, ui/src/index.css:45
  Headline has `gradient-text` class (defined in index.css as `from-blue-400 to-indigo-400`). Strong AI tell.
  → fix: Use solid ink. Use weight or display face for emphasis.
  *Safety: Pure CSS change. Zero functional risk.*

[critical] Glassmorphism without purpose — ui/src/index.css:41, ui/src/pages/CandidateList.jsx (multiple), ui/src/pages/CandidateDetail.jsx:419, ui/src/components/SystemLogDrawer.jsx:97
  `glass-panel` and `backdropFilter: 'blur(16px)'` used heavily on search bars, candidate cards, modals, and telemetry drawers.
  → fix: Remove frosted glass unless overlaying content. Use solid surfaces.
  *Safety: Pure CSS change. Zero functional risk.*

[critical] Purple-gradient / AI Purple — ui/src/pages/CandidateList.jsx:511, 759, 761, ui/src/pages/CandidateDetail.jsx:486, 488
  Progress bars and AI tags use `from-indigo-500 to-purple-500` or `from-indigo-500 via-purple-500 to-pink-500`. Classic AI look.
  → fix: Pick one solid anchor hue. No gradients for status.
  *Safety: Pure CSS styling change. Keep dynamic width interpolation (`style={{ width: ... }}`) and SSE status conditions intact.*

[major] Lucide icons — ui/src/pages/CandidateList.jsx:2, ui/src/pages/CandidateDetail.jsx:3
  Lucide is discouraged AI default for premium UI. (SystemLogDrawer avoids this by using emoji, which is another issue).
  → fix: Swap to Phosphor, hugeicons, or Radix icons globally.
  > ⚠️ **EXTRA CAREFUL (POTENTIAL FUNCTIONAL RISK):** Swapping icon packages requires adding new npm dependency. Ensure all event handlers attached to icon wrappers (such as `onClick`, `e.stopPropagation()`, button triggers for file downloads, deletions, and menu toggles) and props (`size`, `className`, `aria-hidden`) are strictly preserved.

[major] Sparkle icon as AI shortcut — ui/src/pages/CandidateList.jsx:609, 730, 744, 770, ui/src/pages/CandidateDetail.jsx:450, 466, 498
  `<Sparkles>` icon used for "AI Extraction" and "Match". Cliché AI-tool shortcut.
  → fix: Lead with typography or use a custom mark / badge.
  *Safety: Ensure conditional rendering logic for `used_ai_fallback` and SSE status triggers remain untouched.*

Summary — 3 critical · 2 major · 0 minor
Verdict — reads as AI-generated

---

## 2. Design-Taste-Frontend Audit

- **Lila Rule (Purple/Blue)**: Violated globally. Indigo/purple used heavily for primary actions, borders, and AI tags across all pages.
  *Safety: Pure CSS color token swap. Zero functional risk.*
- **Glassmorphism**: Violated globally. Used as default container background.
  *Safety: Pure CSS surface replacement. Zero functional risk.*
- **Inter-everywhere (Typography)**: Violated. `SystemLogDrawer.jsx` hardcodes `fontFamily: 'Inter, system-ui, sans-serif'` and tailwind uses default sans. A one-font page is a template page.
  → fix: Pair a distinctive display face with a refined body face.
  *Safety: Font imports / CSS only. Zero functional risk.*

---

## 3. Impeccable Critique & Layout Structure

- **Heuristic Score**: Low on distinctiveness. UI relies on AI cliché visual language (purple gradients, sparkles, glass panels, 3-column feature grid layout for cards).
- **Action**: Needs `distill` and layout refinement pass to remove generic SaaS feeling.
  > ⚠️ **EXTRA CAREFUL (POTENTIAL FUNCTIONAL RISK):** If refactoring card layouts, grid structure, or list views:
  > 1. Maintain candidate card click navigation (`onClick={() => navigate('/candidate/' + id)}`).
  > 2. Maintain checkbox multi-selection bubbling prevention (`toggleSelectCandidate(e, id)` with `e.stopPropagation()`).
  > 3. Preserve context action menus (`toggleMenu`), direct file download links, and delete confirmation modal triggers.
  > 4. Preserve live SSE streaming progress bars and batch status indicators inside candidate cards.

---

## 4. Humanise-Text Review (docs/architecture_design_document.md)

- Document reads like standard technical writing.
- **AI Pattern spotted**: "scales seamlessly" (Line 17). "Seamlessly" is a very common AI filler word.
  → fix: Replace with concrete metric or drop word. "Scales to 100,000+ candidates" is enough.
  *Safety: Text documentation edit only. Zero functional code risk.*
