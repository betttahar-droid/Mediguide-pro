# The prop corpus (slim)

98 finished props, carried on this branch **only** so a local checkout can
reproduce the sweeps. It is normally gitignored — it is generated scratch, not
source.

**What is here:** the state each tool reads and cannot recompute without a model
call — `parts_front.json`, `strips_front.json`, `scale_rules.json`,
`layers_front.json`, `geometry_audit.json`, the profiles — plus the four bought
elevations per prop, the painted background plate, and all 2308 part masks.

**What is not:** the round renders, `_audit/`, `export/` and the debug PNGs.
That is 810 MB of the original 2.2 GB and every byte of it regenerates from
what is here. 120 MB against 2.2 GB is why the branch exists at all.

**Verified faithful** against the working tree at the time it was cut:
98 `parts_front.json`, 98 `strips_front.json`, 68 `scale_rules.json`
(30 props genuinely never had one), 100 `front.png`, 98 `geometry_audit.json`,
2308 masks — every count matching.

## Using it

```bash
git fetch origin corpus-data
git checkout corpus-data -- tools/img2threejs-work
git checkout claude/prop-maker-tool-repo-xun9e0     # back to the code
```

The folder is gitignored on the code branch, so it simply stays put.

Then, with the dev server up:

```bash
npx vite --port 5173 &
python3 tools/authoring/geometry_sweep.py --save   # baseline, ~8 min
python3 tools/authoring/scale_check.py
```

## Delete it when you are done

It costs the repository ~120 MB forever otherwise:

```bash
git push origin --delete corpus-data
```
