# UI quality rules

Binding for every change to `design_canvas/static/` and to user-facing copy. The owner stated rules 1 and 2 and approved rules 3 to 10 on 2026-11-22. They are in addition to the accessibility and keyboard rules of PRD section 8 and the hard rules in `CLAUDE.md`.

## The rules

1. No thick accent border on one side of a card, callout, alert, list item or quote (for example `border-left: 4px solid <accent>`). Use spacing, type weight, an icon or a full hairline border instead.
2. No "soft tinted background with a thin border of the same hue" as the default way to mark a status, tag, callout or card. One neutral surface and one clear signal (text, icon or a solid chip) is enough.
3. No gradient text and no purple-to-blue gradient as a default accent.
4. No blur or glass panels, and no drop shadow plus large radius on every card.
5. No emoji used as icons or bullets, and no sparkle marks.
6. No pill or badge on things that are not states. No all-caps, letter-spaced micro labels as section decoration.
7. No centred hero with a slogan in an application screen. Screens open on the user's task.
8. One accent colour, used for the primary action and the current selection. Status colours only for status.
9. Dense, aligned layouts on a consistent spacing scale. No card grid where a table or a list is the right form.
10. User-facing copy is plain and specific: no filler, no exclamation marks, and the same word for the same thing everywhere.

## How they are applied

- A UI ticket starts with the `ui-ux-pro-max` skill (`.claude/skills/ui-ux-pro-max/`): search its design system for the product type before designing, with `python .claude/skills/ui-ux-pro-max/scripts/search.py "<query>" --domain ux`.
- A UI ticket ends with a check of the changed screens against this list. The pull request says which rules were checked and what was found.
- User-facing copy, documentation and pull request text go through the `unslop` skill (`.claude/skills/unslop/`) before the pull request is opened.
- Enforcement is by the review gate: Code Reviewer reads every diff against this file. Rule 1 can be linted with a search for `border-left` and `border-right` with a width of 3 px or more; rule 2 cannot be detected reliably from CSS and needs a reader.
- The Frontend Developer, Accessibility Auditor and Code Reviewer roles name this file in their checklists.
- Existing screens that break a rule are listed in a ticket, not fixed as a side effect of another ticket.
