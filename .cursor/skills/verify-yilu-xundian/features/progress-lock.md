# Progress lock

平原 stays grey-locked (`未开`) until 涿郡 is cleared (`cleared >= 10`). 徐州 / 吕布 remain locked without boards.

## Sub-features

- `pingyuan-locked` shows 平原 as not enterable on a fresh install.
- `pingyuan-open` (after progress) shows `可入` and allows 驿程.
- `xuzhou-locked` stays non-playable (card / preview only).

## How to get to it (user POV)

- Open 章节 on a fresh install to see 平原 `未开`.
- After clearing all ten 涿郡 stations in real play, reopen 章节.

## Driving it with control_yilu

Preconditions:

- Fresh install or known `cleared` state. There is no shipped debug setter; advancing `cleared` requires real clears or a tester-provided save.

- **Locked proof.** Cold launch → `drive chapter-list` → `evidence --label pingyuan-locked`. PNG/list shows 平原 `未开` and rejects entry.
- **Open proof.** Only after 涿郡 cleared: same drive shows `可入` and `drive` into 平原 驿程 succeeds. Label `pingyuan-open`.

## Gotchas

- Do not fake unlock by editing Preferences in a ship proof unless the recipe documents the exact `hdc` file and restores it in cleanup.
- Skin preview for later chapters is not an unlock.
