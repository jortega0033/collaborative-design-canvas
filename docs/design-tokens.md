# Design tokens

The page uses the Pipenzo "Flow look" tokens: a black page, Flow-style alpha layers, one accent (Pipenzo yellow `#FECE02`), red only for danger.

## Source and resync

- Source: `jortega0033/clip-to-reel-studio`, `extension/sidepanel/tokens.css`, commit `a13378ce73e5b27213c9a200fc960ec93afef054` (2026-11-21).
- Copy: `design_canvas/static/tokens.css`. Do not edit it.
- Resync: copy the source file over `design_canvas/static/tokens.css`. Nothing else changes. Its header comment holds the contrast numbers and a yellow rule that differs from the rules below: it names the primary button, the current-step node and three source-app uses (the "your turn" chip, the hero kicker dot, the overlay opening dot), and it does not name the current selection. For this page the section "Accent, selection and focus" applies: primary action, current-step marker, current selection. The copy must stay identical to the source, so the comment is not edited here. Where the comment and this document differ, this document takes precedence.
- Served at `/tokens.css` (static allowlist in `design_canvas/server.py`) and linked in `index.html` before `styles.css`.

## Rule

New UI uses these tokens. No new colour literals in `styles.css` or `app.js`. Canvas code reads a token with `getComputedStyle(document.documentElement).getPropertyValue('--token')`. Colours that are user data (layer fills, the colour input's default) stay literals.

## Accent, selection and focus

- D1, current selection. The yellow accent is used for the primary action, the current-step marker and the current selection (UI rule 8). Source: decided by the owner on 2026-11-23. How: a selection uses a solid `--primary` fill with `--on-primary` text, not only a yellow border (a yellow border has about 1.5:1 against white on light). It also carries a second sign that is not colour (weight, icon or text) and the existing aria attribute. Never a tint with a same-hue border and never a thick one-sided border. Source of the "How" part: recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.
- D2, focus ring. `--focus` is a focus indicator and is exempt from the accent limit, including where it is yellow in dark. A ticket that says the focus style stays unchanged means the rule on `main` after the token pull request. Source: recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.
- D3, themes. Contrast and no-colour-alone checks cover both the light and the dark block of `tokens.css`. Source: recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.

Status of the page: D1 applies to the selected rows of the project list and the layer list (`.project-list button[aria-current="true"]` and `.layer-list button[aria-current="true"]` in `styles.css`). They are neutral today: `--bg-raised` with a 2px inset `--fg` ring, font-weight 600 and `aria-current` already present. They do not follow D1 yet. No open ticket covers them yet, and this document does not claim it is done.

The canvas selection outline is different. It is a two-tone `--on-ink`/`--ink` dashed outline around layers whose fill is user data and stays as it is. It has no text, so the solid-fill part of D1 does not apply to it. It must not become a yellow-only border (about 1.5:1 against white).

## Light and dark

Dark is the primary design. The light block in `:root` is the matching light theme. The theme follows the operating system colour scheme (`prefers-color-scheme`); there is no switch in the page.

## Token names by role

| Role | Tokens |
|---|---|
| Surfaces | `--bg` (page), `--surface` (panels), `--bg-raised` (inputs, buttons, layer list, so the sunken hover stays visible), `--bg-sunken` (wells, disabled) |
| Text | `--fg`, `--muted`, `--faint` (captions, disabled) |
| Lines | `--border`, `--hairline`, `--control-border` (input and button edges) |
| Dark block | `--ink`, `--on-ink`, `--on-ink-muted`, `--ink-border` (page header; the canvas scene uses `--on-ink` as paper and `--ink` for the selection outline) |
| Accent | `--primary`, `--primary-press`, `--primary-edge`, `--on-primary`. Yellow only on the primary action, the current-step marker and the current selection (UI rule 8). `--focus` is separate, see below. |
| Status | `--danger`, `--danger-bg`, `--success`, `--ok`, `--ok-bg`, `--warn-fg`, `--warn-bg`, `--info` |
| Focus | `--focus` (a focus indicator, exempt from the accent limit) |
| Hero, glass, state layers, shadows | `--hero-*`, `--glass*`, `--scrim`, `--state-*`, `--shadow-*`, `--blur` |
| Type, space, shape, motion | `--font`, `--font-display`, `--mono`, `--space-1` to `--space-7`, `--radius-*`, `--dur-*`, `--ease-*` |
