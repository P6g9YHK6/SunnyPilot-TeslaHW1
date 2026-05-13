#!/usr/bin/env bash

if [[ ! "${BASH_SOURCE[0]}" = "${0}" ]]; then
  echo "Invalid invocation! This script must not be sourced."
  echo "Run 'op.sh' directly or check your .bashrc for a valid alias"
  return 0
fi

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
UNDERLINE='\033[4m'
BOLD='\033[1m'
NC='\033[0m'

SHELL_NAME="$(basename ${SHELL})"
RC_FILE="${HOME}/.$(basename ${SHELL})rc"
if [ "$(uname)" == "Darwin" ] && [ $SHELL == "/bin/bash" ]; then
  RC_FILE="$HOME/.bash_profile"
fi

# =====================
# FORK CONFIG
# =====================
declare -A FORKS REPOS BRANCHES COMMENTS
FORK_COUNT=0
UNDECLARED_COUNT=0
UNDECLARED_KEYS=()
UNDECLARED_BRANCHES=()

function op_load_fork_config() {
  local conf
  conf="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd)/forks.conf"
  [[ ! -f "$conf" ]] && return
  FORK_COUNT=0
  while IFS=' ' read -r num repo branch comment; do
    [[ -z "$num" || "$num" =~ ^# ]] && continue
    FORKS[$num]="${repo%/*}"
    REPOS[$num]="${repo#*/}"
    BRANCHES[$num]="$branch"
    [[ -n "$comment" ]] && COMMENTS[$num]="$comment"
    FORK_COUNT=$num
  done < "$conf"
}

op_load_fork_config

FORKS_DIR="forks"

function op_ensure_forks_dir() {
  if [ -d "/data/$FORKS_DIR" ]; then
    return 0
  fi
  echo -e "Fork directory /data/$FORKS_DIR does not exist."
  echo -e "This will be used to store all fork repositories."
  read -p "Create /data/$FORKS_DIR? [Y/n] " confirm
  case "$confirm" in
    n|N|no|NO) echo -e " ↳ [${RED}✗${NC}] Aborted. Edit tools/forks.conf or create /data/$FORKS_DIR manually."; return 1 ;;
    *) op_run_command mkdir -p "/data/$FORKS_DIR" ;;
  esac
}

function op_install() {
  echo "Installing op system-wide..."
  CMD="\nalias op='"$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )/op.sh" \"\$@\"'\n"
  grep "alias op=" "$RC_FILE" &> /dev/null || printf "$CMD" >> $RC_FILE
  echo -e " ↳ [${GREEN}✔${NC}] op installed successfully. Open a new shell to use it."
}

function retry() {
  local attempts=$1
  shift
  for i in $(seq 1 "$attempts"); do
    if "$@"; then
      return 0
    fi
    if [ "$i" -lt "$attempts" ]; then
      echo "  Attempt $i/$attempts failed, retrying in 5s..."
      sleep 5
    fi
  done
  return 1
}

function op_run_command() {
  CMD="$@"

  echo -e "${BOLD}Running command →${NC} $CMD │"
  local i
  for ((i=0; i<$((19 + ${#CMD})); i++)); do
    echo -n "─"
  done
  echo -e "┘\n"

  if [[ -z "$DRY" ]]; then
    eval "$CMD"
  fi
}

# be default, assume openpilot dir is in current directory
OPENPILOT_ROOT=$(pwd)
function op_get_openpilot_dir() {
  # First try traversing up the directory tree
  while [[ "$OPENPILOT_ROOT" != '/' ]];
  do
    if find "$OPENPILOT_ROOT/launch_openpilot.sh" -maxdepth 1 -mindepth 1 &> /dev/null; then
      return 0
    fi
    OPENPILOT_ROOT="$(readlink -f "$OPENPILOT_ROOT/"..)"
  done

  # Fallback to hardcoded directories if not found
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
  for dir in "${SCRIPT_DIR%/tools}" "$HOME/openpilot" "/data/openpilot"; do
    if [[ -f "$dir/launch_openpilot.sh" ]]; then
      OPENPILOT_ROOT="$dir"
      return 0
    fi
  done
}

function op_install_post_commit() {
  op_get_openpilot_dir
  if [[ ! -d $OPENPILOT_ROOT/.git/hooks/post-commit.d ]]; then
    mkdir $OPENPILOT_ROOT/.git/hooks/post-commit.d
    mv $OPENPILOT_ROOT/.git/hooks/post-commit $OPENPILOT_ROOT/.git/hooks/post-commit.d 2>/dev/null || true
  fi
  cd $OPENPILOT_ROOT/.git/hooks
  ln -sf ../../scripts/post-commit post-commit
}

function op_check_openpilot_dir() {
  echo "Checking for openpilot directory..."
  if [[ -f "$OPENPILOT_ROOT/launch_openpilot.sh" ]]; then
    echo -e " ↳ [${GREEN}✔${NC}] openpilot found."
    return 0
  fi

  echo -e " ↳ [${RED}✗${NC}] openpilot directory not found! Make sure that you are"
  echo "       inside the openpilot directory or specify one with the"
  echo "       --dir option!"
  return 1
}

function op_check_git() {
  echo "Checking for git..."
  if ! command -v "git" > /dev/null 2>&1; then
    echo -e " ↳ [${RED}✗${NC}] git not found on your system!"
    return 1
  else
    echo -e " ↳ [${GREEN}✔${NC}] git found."
  fi

  echo "Checking for git lfs files..."
  if [[ $(file -b $OPENPILOT_ROOT/selfdrive/modeld/models/dmonitoring_model.onnx) == "data" ]]; then
    echo -e " ↳ [${GREEN}✔${NC}] git lfs files found."
  else
    echo -e " ↳ [${RED}✗${NC}] git lfs files not found! Run 'git lfs pull'"
    return 1
  fi

  echo "Checking for git submodules..."
  for name in $(git config --file .gitmodules --get-regexp path | awk '{ print $2 }' | tr '\n' ' '); do
    if [[ -z $(ls $OPENPILOT_ROOT/$name) ]]; then
      echo -e " ↳ [${RED}✗${NC}] git submodule $name not found! Run 'git submodule update --init --recursive'"
      return 1
    fi
  done
  echo -e " ↳ [${GREEN}✔${NC}] git submodules found."
}

function op_check_os() {
  echo "Checking for compatible os version..."
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then

    if [ -f "/etc/os-release" ]; then
      source /etc/os-release
      case "$VERSION_CODENAME" in
        "jammy" | "kinetic" | "noble" | "focal")
          echo -e " ↳ [${GREEN}✔${NC}] Ubuntu $VERSION_CODENAME detected."
          ;;
        * )
          echo -e " ↳ [${RED}✗${NC}] Incompatible Ubuntu version $VERSION_CODENAME detected!"
          return 1
          ;;
      esac
    else
      echo -e " ↳ [${RED}✗${NC}] No /etc/os-release on your system. Make sure you're running on Ubuntu, or similar!"
      return 1
    fi

  elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e " ↳ [${GREEN}✔${NC}] macOS detected."
  else
    echo -e " ↳ [${RED}✗${NC}] OS type $OSTYPE not supported!"
    return 1
  fi
}

function op_check_venv() {
  echo "Checking for venv..."
  if [[ -f $OPENPILOT_ROOT/.venv/bin/activate ]]; then
    echo -e " ↳ [${GREEN}✔${NC}] venv detected."
  else
    echo -e " ↳ [${RED}✗${NC}] Can't activate venv in $OPENPILOT_ROOT. Assuming global env!"
  fi
}

function op_before_cmd() {
  if [[ ! -z "$NO_VERIFY" ]]; then
    return 0
  fi

  op_get_openpilot_dir
  cd $OPENPILOT_ROOT

  result="$((op_check_openpilot_dir ) 2>&1)" || (echo -e "$result" && return 1)
  result="${result}\n$(( op_check_git ) 2>&1)" || (echo -e "$result" && return 1)
  result="${result}\n$(( op_check_os ) 2>&1)" || (echo -e "$result" && return 1)
  result="${result}\n$(( op_check_venv ) 2>&1)" || (echo -e "$result" && return 1)

  op_activate_venv

  if [[ -z $VERBOSE ]]; then
    echo -e "${BOLD}Checking system →${NC} [${GREEN}✔${NC}]"
  else
    echo -e "$result"
  fi
}

function op_setup() {
  op_get_openpilot_dir
  cd $OPENPILOT_ROOT

  op_check_openpilot_dir
  op_check_os

  echo "Installing dependencies..."
  st="$(date +%s)"
  SETUP_SCRIPT="tools/setup_dependencies.sh"
  if ! $OPENPILOT_ROOT/$SETUP_SCRIPT; then
    echo -e " ↳ [${RED}✗${NC}] Dependencies installation failed!"
    return 1
  fi
  et="$(date +%s)"
  echo -e " ↳ [${GREEN}✔${NC}] Dependencies installed successfully in $((et - st)) seconds."

  op_activate_venv

  echo "Getting git submodules..."
  st="$(date +%s)"
  if ! retry 3 git submodule update --jobs 4 --init --recursive; then
    echo -e " ↳ [${RED}✗${NC}] Getting git submodules failed!"
    return 1
  fi
  et="$(date +%s)"
  echo -e " ↳ [${GREEN}✔${NC}] Submodules installed successfully in $((et - st)) seconds."

  echo "Pulling git lfs files..."
  st="$(date +%s)"
  if ! retry 3 git lfs pull; then
    echo -e " ↳ [${RED}✗${NC}] Pulling git lfs files failed!"
    return 1
  fi
  et="$(date +%s)"
  echo -e " ↳ [${GREEN}✔${NC}] Files pulled successfully in $((et - st)) seconds."

  op_check
}

function op_auth() {
  op_before_cmd
  op_run_command tools/lib/auth.py "$@"
}

function op_activate_venv() {
  # bash 3.2 can't handle this without the 'set +e'
  set +e
  source $OPENPILOT_ROOT/.venv/bin/activate &> /dev/null || true
  set -e

  # persist venv on PATH across GitHub Actions steps
  if [ -n "$GITHUB_PATH" ]; then
    echo "$OPENPILOT_ROOT/.venv/bin" >> "$GITHUB_PATH"
  fi
}

function op_venv() {
  op_before_cmd

  if [[ ! -f $OPENPILOT_ROOT/.venv/bin/activate ]]; then
    echo -e "No venv found in $OPENPILOT_ROOT"
    return 1
  fi

  case $SHELL_NAME in
    "zsh")
      ZSHRC_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'tmp_zsh')
      echo "source $RC_FILE; source $OPENPILOT_ROOT/.venv/bin/activate" >> $ZSHRC_DIR/.zshrc
      ZDOTDIR=$ZSHRC_DIR zsh ;;
    *)
      bash --rcfile <(echo "source $RC_FILE; source $OPENPILOT_ROOT/.venv/bin/activate") ;;
  esac
}

function op_adb() {
  op_before_cmd
  op_run_command tools/scripts/adb_ssh.sh "$@"
}

function op_ssh() {
  op_before_cmd
  op_run_command tools/scripts/ssh.py "$@"
}

function op_script() {
  op_before_cmd

  case $1 in
    som-debug )  op_run_command panda/scripts/som_debug.sh "${@:2}" ;;
    * )
      echo -e "Unknown script '$1'. Available scripts:"
      echo -e "  ${BOLD}som-debug${NC}    SOM serial debug console via panda"
      return 1
      ;;
  esac
}

function op_check() {
  VERBOSE=1
  op_before_cmd
  unset VERBOSE
}

function op_esim() {
  op_before_cmd
  op_run_command system/hardware/esim.py "$@"
}

function op_build() {
  CDIR=$(pwd)
  op_before_cmd
  cd "$CDIR"
  if [[ -f "/AGNOS" ]]; then
    # needed on AGNOS to not run out of memory
    op_run_command system/manager/build.py
  else
    # scons is fine on PC
    op_run_command scons $@
  fi
}

function op_juggle() {
  op_before_cmd
  op_run_command tools/plotjuggler/juggle.py $@
}

function op_lint() {
  op_before_cmd
  op_run_command scripts/lint/lint.sh $@
}

function op_test() {
  op_before_cmd
  op_run_command pytest $@
}

function op_replay() {
  op_before_cmd
  op_run_command tools/replay/replay $@
}

function op_cabana() {
  op_before_cmd
  op_run_command tools/cabana/cabana $@
}

function op_sim() {
  op_before_cmd
  op_run_command exec tools/sim/run_bridge.py &
  op_run_command exec tools/sim/launch_openpilot.sh
}

function op_clip() {
  op_before_cmd
  op_run_command tools/clip/run.py $@
}

# =====================
# FORK HELPERS
# =====================
function op_repo_key() {
  echo "${FORKS[$1]}_${REPOS[$1]}"
}

function op_repo_path() {
  echo "/data/${FORKS_DIR}/$(op_repo_key $1)"
}

function op_detect_active() {
  if [ -L /data/openpilot ]; then
    local target
    target=$(readlink /data/openpilot)
    for i in $(seq 1 $FORK_COUNT); do
      local rp=$(op_repo_path $i)
      if [ "$rp" = "$target" ]; then
        local cur_branch
        cur_branch=$(git -C "$rp" branch --show-current 2>/dev/null || true)
        [ "$cur_branch" = "${BRANCHES[$i]}" ] && echo "$i" && return
      fi
    done
  fi
  echo "0"
}

function op_update_fork() {
  local i=$1 rp branch

  if [[ "$i" =~ ^U([0-9]+)$ ]]; then
    local idx=${BASH_REMATCH[1]}
    idx=$((idx - 1))
    [ "$idx" -ge 0 ] && [ "$idx" -lt "$UNDECLARED_COUNT" ] || { echo "Invalid untracked index"; return 1; }
    rp="/data/${FORKS_DIR}/${UNDECLARED_KEYS[$idx]}"
    branch="${UNDECLARED_BRANCHES[$idx]}"
  else
    rp=$(op_repo_path $i)
    branch="${BRANCHES[$i]}"
  fi

  [ ! -d "$rp" ] && echo "Not downloaded" && return
  cd "$rp" || return
  op_run_command git fetch origin
  op_run_command git merge --ff-only "origin/$branch"
  op_run_command git submodule update --init --recursive
}

function op_check_fork_update() {
  local i=$1 rp branch

  if [[ "$i" =~ ^U([0-9]+)$ ]]; then
    local idx=${BASH_REMATCH[1]}
    idx=$((idx - 1))
    [ "$idx" -ge 0 ] && [ "$idx" -lt "$UNDECLARED_COUNT" ] || return 1
    rp="/data/${FORKS_DIR}/${UNDECLARED_KEYS[$idx]}"
    branch="${UNDECLARED_BRANCHES[$idx]}"
  else
    rp=$(op_repo_path $i)
    branch="${BRANCHES[$i]}"
  fi

  cd "$rp" 2>/dev/null || return 1
  GIT_TERMINAL_PROMPT=0 git fetch origin --quiet 2>/dev/null
  git rev-parse -q --verify "origin/$branch" >/dev/null 2>&1 || return 1
  [ "$(git rev-parse HEAD 2>/dev/null)" != "$(git rev-parse "origin/$branch" 2>/dev/null)" ] && return 0
  git submodule foreach --recursive --quiet '
    git fetch origin --quiet 2>/dev/null
    [ "$(git rev-parse HEAD 2>/dev/null)" != "$(git rev-parse "origin/$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" 2>/dev/null)" ] && exit 1
  ' 2>/dev/null
  [ $? -eq 1 ] && return 0 || return 1
}

function op_purge_fork() {
  local i=$1 rp key branch

  if [[ "$i" =~ ^U([0-9]+)$ ]]; then
    local idx=${BASH_REMATCH[1]}
    idx=$((idx - 1))
    [ "$idx" -ge 0 ] && [ "$idx" -lt "$UNDECLARED_COUNT" ] || { echo "Invalid untracked index"; return 1; }
    rp="/data/${FORKS_DIR}/${UNDECLARED_KEYS[$idx]}"
    key="${UNDECLARED_KEYS[$idx]}"
    branch="${UNDECLARED_BRANCHES[$idx]}"
  else
    rp=$(op_repo_path $i)
    key=$(op_repo_key $i)
    branch="${BRANCHES[$i]}"
  fi

  [ ! -d "$rp" ] && echo -e "[${RED}✗${NC}] Fork $key branch $branch not cloned" && return
  [[ "$rp" = "$(readlink /data/openpilot)" ]] && echo -e "[${RED}✗${NC}] Cannot purge active fork" && return

  echo "Purge $(echo "$key" | tr '_' '/'):$branch?"
  read -p "Are you sure? [y/N] " confirm
  case "$confirm" in
    y|Y|yes|YES) ;;
    *) echo "Aborted."; return ;;
  esac

  if [[ "$i" =~ ^U ]]; then
    # Untracked: count undeclared branches in same repo
    local same_repo=0
    for j in $(seq 0 $((UNDECLARED_COUNT - 1))); do
      [ "${UNDECLARED_KEYS[$j]}" = "$key" ] && same_repo=$((same_repo + 1))
    done
    if [ "$same_repo" -le 1 ]; then
      op_run_command rm -rf "$rp"
    else
      op_run_command git -C "$rp" branch -D "$branch" 2>/dev/null || true
    fi
  else
    local shared=0
    for j in $(seq 1 $FORK_COUNT); do
      [ "$(op_repo_key $j)" = "$key" ] && shared=$((shared + 1))
    done
    if [ "$shared" -le 1 ]; then
      op_run_command rm -rf "$rp"
    else
      op_run_command git -C "$rp" branch -D "$branch" 2>/dev/null || true
    fi
  fi
}

function op_repo_downloaded() {
  local rp=$(op_repo_path $1)
  [ -d "$rp" ] && git -C "$rp" rev-parse -q --verify "${BRANCHES[$1]}" >/dev/null 2>&1 && return 0
  return 1
}

function op_list_forks() {
  local active=$(op_detect_active)
  for i in $(seq 1 $FORK_COUNT); do
    local mark="" status="" note=""
    [ "$active" = "$i" ] && mark=" ${GREEN}<-- ACTIVE${NC}"
    if op_repo_downloaded $i; then
      op_check_fork_update $i && status=" ${RED}(update available)${NC}"
    else
      status=" (not downloaded)"
    fi
    [[ -n "${COMMENTS[$i]}" ]] && note=" ${GREEN}(${COMMENTS[$i]})${NC}"
    echo -e "[$i] ${FORKS[$i]}/${REPOS[$i]}:${BRANCHES[$i]}${note}$status$mark"
  done
  local active_target
  active_target=$(readlink /data/openpilot 2>/dev/null || true)
  for j in $(seq 0 $((UNDECLARED_COUNT - 1))); do
    local rp="/data/${FORKS_DIR}/${UNDECLARED_KEYS[$j]}"
    local u=$((j + 1))
    local mark=""
    local note=" ${RED}(untracked)${NC}"
    if [ -n "$active_target" ] && [ "$rp" = "$active_target" ] && \
       [ "$(git -C "$rp" branch --show-current 2>/dev/null)" = "${UNDECLARED_BRANCHES[$j]}" ]; then
      mark=" ${GREEN}<-- ACTIVE${NC}"
    fi
    echo -e "[U$u] $(echo "${UNDECLARED_KEYS[$j]}" | tr '_' '/'):${UNDECLARED_BRANCHES[$j]}${note}$mark"
  done
}

function op_scan_undeclared() {
  UNDECLARED_COUNT=0
  UNDECLARED_KEYS=()
  UNDECLARED_BRANCHES=()

  local forks_dir="/data/${FORKS_DIR}"
  [ ! -d "$forks_dir" ] && return

  # Build lookup of declared branches per repo_key
  declare -A decl_branches
  for i in $(seq 1 $FORK_COUNT); do
    local key=$(op_repo_key $i)
    decl_branches[$key]="${decl_branches[$key]:+${decl_branches[$key]} }${BRANCHES[$i]}"
  done

  for repo_dir in "$forks_dir"/*/; do
    [ -d "$repo_dir/.git" ] || continue
    local url
    url=$(git -C "$repo_dir" config --get remote.origin.url 2>/dev/null || true)
    [ -z "$url" ] && continue

    local repo_key
    repo_key=$(echo "$url" | sed 's|.*/\([^/]*/[^.]*\)\.git|\1|' | tr '/' '_')

    while IFS= read -r branch; do
      [ -z "$branch" ] && continue
      if [ -z "${decl_branches[$repo_key]:-}" ] || ! echo "${decl_branches[$repo_key]}" | grep -qw "$branch"; then
        UNDECLARED_KEYS+=("$repo_key")
        UNDECLARED_BRANCHES+=("$branch")
      fi
    done < <(git -C "$repo_dir" branch --format='%(refname:short)' 2>/dev/null)
  done
  UNDECLARED_COUNT=${#UNDECLARED_KEYS[@]}
}

function op_detect_undeclared() {
  op_scan_undeclared
  if [ "$UNDECLARED_COUNT" -eq 0 ]; then
    echo "All forks under /data/${FORKS_DIR} are declared in forks.conf."
    return
  fi
  echo "Undeclared forks:"
  for j in $(seq 0 $((UNDECLARED_COUNT - 1))); do
    echo "  [U$((j+1))] $(echo "${UNDECLARED_KEYS[$j]}" | tr '_' '/'):${UNDECLARED_BRANCHES[$j]} (untracked)"
  done
}

function op_fork_menu() {
  op_list_forks
  echo ""
  if [ "$UNDECLARED_COUNT" -gt 0 ]; then
    echo "  [1-$FORK_COUNT, U1-U${UNDECLARED_COUNT}]  switch to fork"
    echo "  [u N]    update fork N (or UN for untracked)"
    echo "  [p N]    purge fork N (or UN for untracked)"
  else
    echo "  [1-$FORK_COUNT]  switch to fork (downloads if missing)"
    echo "  [u N]    update fork N"
    echo "  [p N]    purge fork N"
  fi
  echo "  [e]      exit"
  echo ""
}

function op_use_fork() {
  local i=$1 rp branch

  if [[ "$i" =~ ^U([0-9]+)$ ]]; then
    local idx=${BASH_REMATCH[1]}
    idx=$((idx - 1))
    [ "$idx" -ge 0 ] && [ "$idx" -lt "$UNDECLARED_COUNT" ] || { echo "Invalid untracked index"; return 1; }
    rp="/data/${FORKS_DIR}/${UNDECLARED_KEYS[$idx]}"
    branch="${UNDECLARED_BRANCHES[$idx]}"
    cd "$rp" || return
    op_run_command git checkout -f "$branch"
    op_run_command git submodule update --init --recursive
  else
    rp=$(op_repo_path $i)
    mkdir -p "/data/${FORKS_DIR}"
    if [ ! -d "$rp" ]; then
      op_run_command git clone -b "${BRANCHES[$i]}" --depth 1 --single-branch \
        --recurse-submodules --shallow-submodules \
        "https://github.com/${FORKS[$i]}/${REPOS[$i]}.git" "$rp"
    else
      cd "$rp" || return
      op_run_command git fetch origin "${BRANCHES[$i]}:${BRANCHES[$i]}" --depth 1
      op_run_command git checkout -f "${BRANCHES[$i]}"
      op_run_command git submodule update --init --recursive
    fi
  fi

  # Show AGNOS versions and ask for confirmation
  local target_agnos current_agnos
  target_agnos=$(grep -oP 'AGNOS_VERSION="\K[^"]+' "$rp/launch_env.sh" 2>/dev/null || true)
  current_agnos=$(cat /VERSION 2>/dev/null || true)
  if [ -n "$target_agnos" ]; then
    echo "Current AGNOS: ${current_agnos:-unknown}"
    echo "Target AGNOS:  $target_agnos"
    if [ -n "$current_agnos" ] && [ "$current_agnos" != "$target_agnos" ]; then
      echo -e "${RED}Warning: OS will be updated from $current_agnos to $target_agnos${NC}"
    fi
  fi
  read -p "Proceed with switch and reboot? [y/N] " confirm
  case "$confirm" in
    y|Y|yes|YES) ;;
    *) echo "Aborted."; return ;;
  esac

  # First setup: migrate standalone /data/openpilot into /data/forks/ architecture
  if [ -d /data/openpilot ] && [ ! -L /data/openpilot ]; then
    local existing_url existing_repo existing_branch existing_path
    existing_url=$(git -C /data/openpilot config --get remote.origin.url 2>/dev/null)
    existing_branch=$(git -C /data/openpilot rev-parse --abbrev-ref HEAD 2>/dev/null)
    if [ -n "$existing_url" ] && [ -n "$existing_branch" ]; then
      existing_repo=$(echo "$existing_url" | sed 's|.*/\([^/]*/[^.]*\)\.git|\1|' | tr '/' '_')
      existing_path="/data/${FORKS_DIR}/${existing_repo}"
      read -p "Migrate existing /data/openpilot ($existing_repo/$existing_branch) to $existing_path? [y/N] " confirm
      case "$confirm" in
        y|Y|yes|YES) ;;
        *) echo "Aborted."; return ;;
      esac
      echo "Migrating..."
      mkdir -p "$existing_path"
      shopt -s dotglob
      mv /data/openpilot/* "$existing_path/"
      shopt -u dotglob
      rmdir /data/openpilot || echo "Warning: could not remove /data/openpilot (running process?), symlinking over it"
    else
      local bak="/data/openpilot.orig.$(date +%s)"
      read -p "Migrate unknown /data/openpilot to $bak? [y/N] " confirm
      case "$confirm" in
        y|Y|yes|YES) ;;
        *) echo "Aborted."; return ;;
      esac
      echo "Warning: /data/openpilot is not a symlink but origin/branch not detectable"
      echo "Moving it to $bak"
      mv /data/openpilot "$bak"
      op_run_command ln -sfn "$rp" /data/openpilot
      return
    fi
  fi
  op_run_command ln -sfn "$rp" /data/openpilot
  cd /data/openpilot || return
  if [ -f launch_env.sh ] && [ -f /VERSION ]; then
    local required installed
    required=$(grep -oP 'AGNOS_VERSION="\K[^"]+' launch_env.sh 2>/dev/null || true)
    installed=$(cat /VERSION 2>/dev/null || true)
    if [ -n "$required" ] && [ -n "$installed" ] && [ "$installed" != "$required" ]; then
      echo "[OS] Versions differ ($installed vs $required), running OS update..."
      PYTHONPATH=$(pwd) ./system/hardware/tici/agnos.py system/hardware/tici/agnos.json --swap || true
    fi
  fi
  op_run_command sudo reboot
}

function op_fork() {
  if [ $FORK_COUNT -eq 0 ]; then
    echo -e "[${RED}✗${NC}] No forks configured. Edit tools/forks.conf."
    return
  fi

  op_ensure_forks_dir || return 1
  op_scan_undeclared

  # sub-action mode
  case $1 in
    list|ls)    op_list_forks; return ;;
    u|update)   shift; [ -n "$1" ] && op_update_fork "$1" || echo "Usage: op fork u <N|UN>"; return ;;
    p|purge)    shift; [ -n "$1" ] && op_purge_fork "$1" || echo "Usage: op fork p <N|UN>"; return ;;
    d|detect)   op_detect_undeclared; return ;;
    help|-h|--help)
      echo "Usage: op fork [action]"
      echo ""
      echo "Actions:"
      echo "  list              List all forks with status"
      echo "  detect            Scan /data/forks/ for undeclared repos/branches"
      echo "  <N|UN>            Switch to fork (clone + checkout + symlink + reboot)"
      echo "  u <N|UN>          Update fork (fetch + merge --ff-only)"
      echo "  p <N|UN>          Purge fork"
      echo "  help              Show this help"
      echo ""
      echo "  (no action)       Interactive menu"
      return ;;
    [0-9]*|U[0-9]*)
      if [[ "$1" =~ ^U[0-9]+$ ]]; then
        op_use_fork "$1"
      elif [ "$1" -ge 1 ] && [ "$1" -le $FORK_COUNT ] 2>/dev/null; then
        op_use_fork "$1"
      else
        echo "Invalid fork number. Use 1-$FORK_COUNT or U<N>."
      fi
      return ;;
    *)  [ -n "$1" ] && echo "Unknown action '$1'. Run 'op fork help' for usage." && return ;;
  esac

  # interactive menu (no args or unmatched)
  op_fork_menu
  read -p "Select: " opt arg
  case $opt in
    e|E|exit|quit) return ;;
    u|U)    [ -n "$arg" ] && op_update_fork "$arg" || echo "Usage: u <N|UN>" ;;
    p|P)    [ -n "$arg" ] && op_purge_fork "$arg" || echo "Usage: p <N|UN>" ;;
    [1-9][0-9]*|[1-9]|U[0-9]*|u[0-9]*) op_use_fork "${opt^^}" ;;
    *)      echo "Invalid option" ;;
  esac
}

function op_switch() {
  REMOTE="origin"
  if [ "$#" -gt 1 ]; then
    REMOTE="$1"
    shift
  fi

  if [ -z "$1" ]; then
    echo -e "${BOLD}${UNDERLINE}Usage:${NC} op switch [REMOTE] <BRANCH>"
    return 1
  fi
  BRANCH="$1"

  git config --replace-all remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
  git submodule deinit --all --force
  git fetch "$REMOTE" "$BRANCH"
  git checkout -f FETCH_HEAD
  git checkout -B "$BRANCH" --track "$REMOTE"/"$BRANCH"
  git submodule deinit --all --force
  git reset --hard "${REMOTE}/${BRANCH}"
  git clean -df
  git submodule update --init --recursive
  git submodule foreach git reset --hard
  git submodule foreach git clean -df

  # remove openpilot update flag if present
  rm -f .overlay_init
}

function op_start() {
  if [[ -f "/AGNOS" ]]; then
    op_before_cmd
    op_run_command sudo systemctl restart comma $@
  fi
}

function op_stop() {
  if [[ -f "/AGNOS" ]]; then
    op_before_cmd
    op_run_command sudo systemctl stop comma $@
  fi
}

function op_default() {
  echo "An openpilot helper"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Description:${NC}"
  echo "  op is your entry point for all things related to openpilot development."
  echo "  op is only a wrapper for existing scripts, tools, and commands."
  echo "  op will always show you what it will run on your system."
  echo ""
  echo -e "${BOLD}${UNDERLINE}Usage:${NC} op [OPTIONS] <COMMAND>"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Commands [System]:${NC}"
  echo -e "  ${BOLD}auth${NC}         Authenticate yourself for API use"
  echo -e "  ${BOLD}check${NC}        Check the development environment (git, os) to start using openpilot"
  echo -e "  ${BOLD}esim${NC}         Manage eSIM profiles on your comma device"
  echo -e "  ${BOLD}venv${NC}         Activate the python virtual environment"
  echo -e "  ${BOLD}setup${NC}        Install openpilot dependencies"
  echo -e "  ${BOLD}build${NC}        Run the openpilot build system in the current working directory"
  echo -e "  ${BOLD}install${NC}      Install the 'op' tool system wide"
  echo -e "  ${BOLD}switch${NC}       Switch to a different git branch with a clean slate (nukes any changes)"
  echo -e "  ${BOLD}fork${NC}         Manage openpilot forks (list/switch/update/purge)"
  echo -e "  ${BOLD}start${NC}        Starts (or restarts) openpilot"
  echo -e "  ${BOLD}stop${NC}         Stops openpilot"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Commands [Tooling]:${NC}"
  echo -e "  ${BOLD}juggle${NC}       Run PlotJuggler"
  echo -e "  ${BOLD}replay${NC}       Run Replay"
  echo -e "  ${BOLD}cabana${NC}       Run Cabana"
  echo -e "  ${BOLD}clip${NC}         Run clip (linux only)"
  echo -e "  ${BOLD}adb${NC}          Run adb shell"
  echo -e "  ${BOLD}ssh${NC}          comma prime SSH helper"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Commands [Scripts]:${NC}"
  echo -e "  ${BOLD}script${NC}       Run a script (e.g. op script som-debug)"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Commands [Testing]:${NC}"
  echo -e "  ${BOLD}sim${NC}          Run openpilot in a simulator"
  echo -e "  ${BOLD}lint${NC}         Run the linter"
  echo -e "  ${BOLD}post-commit${NC}  Install the linter as a post-commit hook"
  echo -e "  ${BOLD}test${NC}         Run all unit tests from pytest"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Options:${NC}"
  echo -e "  ${BOLD}-d, --dir${NC}"
  echo "          Specify the openpilot directory you want to use"
  echo -e "  ${BOLD}--dry${NC}"
  echo "          Don't actually run anything, just print what would be run"
  echo -e "  ${BOLD}-n, --no-verify${NC}"
  echo "          Skip environment check before running commands"
  echo ""
  echo -e "${BOLD}${UNDERLINE}Examples:${NC}"
  echo "  op setup"
  echo "          Run the setup script to install"
  echo "          openpilot's dependencies."
  echo ""
  echo "  op build -j4"
  echo "          Compile openpilot using 4 cores"
  echo ""
  echo "  op juggle --demo"
  echo "          Run PlotJuggler on the demo route"
}


function _op() {
  # parse Options
  case $1 in
    -d | --dir )       shift 1; OPENPILOT_ROOT="$1"; shift 1 ;;
    --dry )            shift 1; DRY="1" ;;
    -n | --no-verify ) shift 1; NO_VERIFY="1" ;;
  esac

  # parse Commands
  case $1 in
    auth )          shift 1; op_auth "$@" ;;
    venv )          shift 1; op_venv "$@" ;;
    check )         shift 1; op_check "$@" ;;
    esim )          shift 1; op_esim "$@" ;;
    setup )         shift 1; op_setup "$@" ;;
    build )         shift 1; op_build "$@" ;;
    juggle )        shift 1; op_juggle "$@" ;;
    cabana )        shift 1; op_cabana "$@" ;;
    lint )          shift 1; op_lint "$@" ;;
    test )          shift 1; op_test "$@" ;;
    replay )        shift 1; op_replay "$@" ;;
    clip )          shift 1; op_clip "$@" ;;
    sim )           shift 1; op_sim "$@" ;;
    install )       shift 1; op_install "$@" ;;
    switch )        shift 1; op_switch "$@" ;;
    fork )          shift 1; op_fork "$@" ;;
    start )         shift 1; op_start "$@" ;;
    stop )          shift 1; op_stop "$@" ;;
    restart )       shift 1; op_restart "$@" ;;
    post-commit )   shift 1; op_install_post_commit "$@" ;;
    adb )           shift 1; op_adb "$@" ;;
    ssh )           shift 1; op_ssh "$@" ;;
    script )        shift 1; op_script "$@" ;;
    * ) op_default "$@" ;;
  esac
}

_op $@
