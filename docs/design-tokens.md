# Design tokens

The page uses the Pipenzo "Flow look" tokens: a black page, Flow-style alpha layers, one accent (Pipenzo yellow `#FECE02`), red only for danger.

## Source and resync

- Source: `jortega0033/clip-to-reel-studio`, `extension/sidepanel/tokens.css`, commit `a13378ce73e5b27213c9a200fc960ec93afef054` (2026-11-21).
- Copy: `design_canvas/static/tokens.css`. Do not edit it.
- Resync: copy the source file over `design_canvas/static/tokens.css`. Nothing else changes. Its header comment holds the contrast numbers and the yellow rule.
- Served at `/tokens.css` (static allowlist in `design_canvas/server.py`) and linked in `index.html` before `styles.css`.

## Rule

New UI uses these tokens. No new colour literals in `styles.css` or `app.js`. Canvas code reads a token with `getComputedStyle(document.documentElement).getPropertyValue('--token')`. Colours that are user data (layer fills, the colour input's default) stay literals.

## Light and dark

Dark is the primary design. The light block in `:root` is the matching light theme. The theme follows the operating system colour scheme (`prefers-color-scheme`); there is no switch in the page.

## Token names by role

| Role | Tokens |
|---|---|
| Surfaces | `--bg` (page), `--surface` (panels), `--bg-raised` (inputs, buttons, layer list, so the sunken hover stays visible), `--bg-sunken` (wells, disabled) |
| Text | `--fg`, `--muted`, `--faint` (captions, disabled) |
| Lines | `--border`, `--hairline`, `--control-border` (input and button edges) |
| Dark block | `--ink`, `--on-ink`, `--on-ink-muted`, `--ink-border` (page header; the canvas scene uses `--on-ink` as paper and `--ink` for the selection outline) |
| Accent | `--primary`, `--primary-press`, `--primary-edge`, `--on-primary`. Yellow only on the primary action and the current-step marker. |
| Status | `--danger`, `--danger-bg`, `--success`, `--ok`, `--ok-bg`, `--warn-fg`, `--warn-bg`, `--info` |
| Focus | `--focus` |
| Hero, glass, state layers, shadows | `--hero-*`, `--glass*`, `--scrim`, `--state-*`, `--shadow-*`, `--blur` |
| Type, space, shape, motion | `--font`, `--font-display`, `--mono`, `--space-1` to `--space-7`, `--radius-*`, `--dur-*`, `--ease-*` |
