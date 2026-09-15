#!/usr/bin/env bash
# One command to run the prop maker with no paid API.
#
#   bash tools/setup/local-setup.sh
#   bash tools/setup/local-setup.sh --pull      # also download the models
#
# It changes nothing it does not have to: it inspects what you already have,
# writes ONE file (.env.local) and prints what is still missing. Run it as often
# as you like.
#
# WHY A SCRIPT AND NOT A PARAGRAPH OF INSTRUCTIONS. The three things that go
# wrong on a first local run are all silent: Ollama's default context is 4096
# tokens and truncates a prompt carrying four images, ComfyUI's API-format
# export has your checkpoint's filename baked in and nobody else's, and a
# workflow missing {MASK} makes paint_out refuse every hole without saying why.
# Each of those is one line to check and an afternoon to discover.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
COMFY_URL="${COMFY_URL:-http://127.0.0.1:8188}"
TEXT_MODEL="${LOCAL_TEXT_MODEL:-qwen3:8b}"
VISION_MODEL="${LOCAL_VISION_MODEL:-qwen2.5vl:7b}"
WF_SRC="$ROOT/tools/authoring/comfy/inpaint_sdxl.json"
WF_OUT="$ROOT/tools/authoring/comfy/inpaint_ready.json"
ENV_OUT="$ROOT/.env.local"
PULL=0
[ "${1:-}" = "--pull" ] && PULL=1

ok=0; bad=0
say()  { printf '  %s\n' "$*"; }
good() { printf '  \033[32mOK\033[0m   %s\n' "$*"; ok=$((ok+1)); }
warn() { printf '  \033[33mTODO\033[0m %s\n' "$*"; bad=$((bad+1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$*"; }

head_ "Host tools"
for c in python3 node npx; do
  if command -v "$c" >/dev/null 2>&1; then good "$c $("$c" --version 2>&1 | head -1)"
  else warn "$c is not installed"; fi
done
if python3 -c "import PIL, numpy" 2>/dev/null; then good "python: Pillow and numpy"
else warn "pip install pillow numpy"; fi

head_ "Ollama  ($OLLAMA_URL)"
TAGS="$(curl -fsS --max-time 5 "$OLLAMA_URL/api/tags" 2>/dev/null)"
if [ -z "$TAGS" ]; then
  warn "not reachable -- start it with:  ollama serve"
else
  good "reachable"
  for m in "$TEXT_MODEL" "$VISION_MODEL"; do
    base="${m%%:*}"
    if printf '%s' "$TAGS" | grep -q "\"$base"; then good "model $m"
    elif [ "$PULL" = "1" ]; then
      say "pulling $m ..."; ollama pull "$m" && good "model $m" || warn "pull failed: $m"
    else warn "model $m missing   ->  ollama pull $m"; fi
  done
fi

head_ "ComfyUI  ($COMFY_URL)"
STATS="$(curl -fsS --max-time 5 "$COMFY_URL/system_stats" 2>/dev/null)"
if [ -z "$STATS" ]; then
  warn "not reachable -- start ComfyUI, then re-run this"
else
  good "reachable"
  # ASK IT WHAT CHECKPOINTS IT HAS rather than making you paste a filename.
  # An API-format workflow carries the exporter's own checkpoint name, which is
  # the single commonest reason someone else's workflow fails to queue.
  CKPTS="$(curl -fsS --max-time 10 "$COMFY_URL/object_info/CheckpointLoaderSimple" 2>/dev/null \
    | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
    print("\n".join(d["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]))
except Exception: pass' 2>/dev/null)"
  if [ -z "$CKPTS" ]; then
    warn "could not list checkpoints -- is any model installed?"
  else
    N=$(printf '%s\n' "$CKPTS" | grep -c .)
    good "$N checkpoint(s) installed"
    # prefer one that says inpaint; the graph uses VAEEncodeForInpaint, which
    # works with an ordinary checkpoint too, just less cleanly.
    PICK="$(printf '%s\n' "$CKPTS" | grep -i -m1 'inpaint' || true)"
    [ -z "$PICK" ] && PICK="$(printf '%s\n' "$CKPTS" | grep -i -m1 -E 'xl|flux' || true)"
    [ -z "$PICK" ] && PICK="$(printf '%s\n' "$CKPTS" | head -1)"
    say "using checkpoint: $PICK"
    printf '%s\n' "$CKPTS" | grep -qi inpaint || \
      say "  (no inpainting checkpoint found -- this will work, but an"
    printf '%s\n' "$CKPTS" | grep -qi inpaint || \
      say "   inpaint model gives much cleaner holes)"
    PICK="$PICK" python3 - "$WF_SRC" "$WF_OUT" <<'PY'
import json, os, sys
src, out = sys.argv[1], sys.argv[2]
g = json.load(open(src))
g["1"]["inputs"]["ckpt_name"] = os.environ["PICK"]
json.dump(g, open(out, "w"), indent=1)
missing = [k for k in ("{PROMPT}", "{IMAGE}", "{MASK}", "{SEED}")
           if k not in json.dumps(g)]
print(f"  \033[32mOK\033[0m   workflow written: {out}")
if missing:
    print(f"  \033[33mTODO\033[0m placeholders missing: {' '.join(missing)}")
PY
  fi
fi

head_ "Writing $ENV_OUT"
cat > "$ENV_OUT" <<EOF
# Written by tools/setup/local-setup.sh. Source it before a build:
#     set -a; . ./.env.local; set +a
# Unset PROP_IMAGE_BACKEND / PROP_LLM_BACKEND to go back to the paid path.
PROP_IMAGE_BACKEND=comfy
COMFY_URL=$COMFY_URL
COMFY_WORKFLOW=$WF_OUT

PROP_LLM_BACKEND=ollama
OLLAMA_URL=$OLLAMA_URL
LOCAL_TEXT_MODEL=$TEXT_MODEL
LOCAL_VISION_MODEL=$VISION_MODEL
EOF
good "$ENV_OUT"

head_ "Verifying through the tool's own checks"
set -a; . "$ENV_OUT"; set +a
python3 "$ROOT/tools/authoring/local_llm.py" --check
python3 "$ROOT/tools/authoring/comfy_backend.py" --check

head_ "Result"
say "$ok ready, $bad to do"
if [ "$bad" -eq 0 ]; then
  cat <<'EOF'

  Ready. Start the renderer's dev server, then build a prop:

      npx vite --port 5173 &
      set -a; . ./.env.local; set +a
      python3 tools/authoring/make_prop.py "arcade cabinet" --out work/test

  Try paint_out on its own first -- it is the biggest image cost and the
  stage a local inpaint improves most:

      python3 tools/authoring/paint_out.py work/test --asset "arcade cabinet"
EOF
else
  say ""
  say "Fix the TODO lines above and run this again."
fi
exit 0
