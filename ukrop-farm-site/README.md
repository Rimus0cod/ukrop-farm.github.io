# UKROP FARM — GitHub Pages

Static one-page landing for the amateur Dota 2 team **Ukrop Farm**.

## Deploy

1. Put all files in the root of a GitHub repository named `<username>.github.io`, or any repo with GitHub Pages enabled.
2. Push the files.
3. In GitHub: **Settings → Pages → Deploy from branch → main / root**.

No build step is required.

## Update the roster

Open `roster.js` and replace the five placeholder objects:

- `nick` — player nickname
- `name` — short role label / real name if desired
- `role` — e.g. POSITION 1
- `steam` — the player's Steam profile URL
- `active` — `true` for the active five, `false` for standby

The page automatically renders the cards from that array.

## Team data

Current team ID displayed by the supplied team page screenshot: `10272953`.
