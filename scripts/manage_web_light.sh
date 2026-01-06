#!/bin/bash
set -euo pipefail
# Manage web_light modules: add, remove, list
# Usage:
#   ./scripts/manage_web_light.sh list
#   ./scripts/manage_web_light.sh add module1 module2
#   ./scripts/manage_web_light.sh remove module1 module2

ROOT_DIR="$(pwd)"
OUT_DIR="$ROOT_DIR/web/build"

usage(){
  echo "Usage: $0 list|add|remove [modules...]"
  exit 1
}

if [ $# -lt 1 ]; then usage; fi
CMD="$1"; shift || true

current=()
if [ -f "$OUT_DIR/modules.txt" ]; then
  read -r -a current < "$OUT_DIR/modules.txt"
fi

case "$CMD" in
  list)
    echo "Current modules in web/build:"
    printf '%s\n' "${current[@]}"
    ;;
  add)
    if [ $# -lt 1 ]; then echo "No modules to add"; exit 1; fi
    new=(${current[@]})
    for m in "$@"; do
      case " ${new[@]} " in *" $m "*) echo "$m already present" ;; *) new+=("$m") ;;
      esac
    done
    echo "Building with modules: ${new[@]}"
    ./scripts/assemble_web_light.sh ${new[@]}
    ;;
  remove)
    if [ $# -lt 1 ]; then echo "No modules to remove"; exit 1; fi
    # compute remaining
    rem=()
    for cm in "${current[@]}"; do
      skip=0
      for rmv in "$@"; do [ "$cm" = "$rmv" ] && skip=1 && break; done
      [ $skip -eq 0 ] && rem+=("$cm")
    done
    echo "Building with modules: ${rem[@]}"
    if [ ${#rem[@]} -gt 0 ]; then
      ./scripts/assemble_web_light.sh ${rem[@]}
    else
      # no modules left; remove build
      rm -rf "$OUT_DIR" && mkdir -p "$OUT_DIR"
      echo "No modules left; web/build cleared."
    fi
    ;;
  *) usage ;;
esac
