# Progress lock

平原 stays grey-locked (`未开`) until 涿郡 is cleared (`cleared >= 10`). 徐州 / 吕布 remain locked without boards.

## Sub-features

- `pingyuan-locked` shows 平原 as not enterable on a fresh install.
- `pingyuan-open` (after progress) shows `可入` and allows 驿程.
- `xuzhou-locked` stays non-playable (list card only; tap is a no-op, no skin preview).

## How to get to it (user POV)

- Open 章节 on a fresh install to see 平原 `未开`.
- After clearing all ten 涿郡 stations in the same session (do not force-stop), reopen 章节.

## Driving it with control_yilu

Preconditions:

- Cold launch or known in-session `cleared`. Progress is `@State` RAM only (starts at 0); `cleanup` / force-stop resets it. There is no shipped debug setter and no Preferences file. Advancing `cleared` requires real clears in the same process.

- **Locked proof.** Cold launch → `drive chapter-list` → `evidence --label pingyuan-locked`. JPEG/list shows 平原 `未开` and rejects entry.
- **Open proof.** Only after 涿郡 is cleared (`cleared >= 10`): `drive chapter-list` shows 平原 `可入`. No `drive` feature opens 平原; tap the 平原 card to reach `平原·驿程`. Label `pingyuan-open`.

## Gotchas

- Do not invent a Preferences or hdc save file; none ships. Force-stop wipes `cleared`.
- Skin preview for later chapters is not an unlock.
