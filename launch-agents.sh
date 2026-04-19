#!/usr/bin/env bash
# launch-agents.sh — Create TMUX session 'reclaim' with 4 Claude Code agent panes
# Each pane runs a Claude Code instance scoped to a specific RECLAIM subsystem
set -euo pipefail

SESSION="reclaim"
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

GREEN='\033[0;32m'
NC='\033[0m'
info() { echo -e "${GREEN}[+]${NC} $1"; }

# Kill existing session if running
if tmux has-session -t "$SESSION" 2>/dev/null; then
    read -p "Session '$SESSION' already exists. Kill it? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        tmux kill-session -t "$SESSION"
    else
        echo "Attaching to existing session..."
        tmux attach -t "$SESSION"
        exit 0
    fi
fi

info "Creating TMUX session: $SESSION"
info "Repo root: $REPO_ROOT"

# ── Create session with first pane (Perception) ──────────────────────────────
tmux new-session -d -s "$SESSION" -n "agents" -c "$REPO_ROOT"

# Pane 0: Perception Agent
tmux send-keys -t "$SESSION:agents.0" \
    "claude --system-prompt \"\$(cat $REPO_ROOT/.agents/perception.md)\"" Enter

# Split horizontally: Pane 1 (Navigation Agent)
tmux split-window -h -t "$SESSION:agents" -c "$REPO_ROOT"
tmux send-keys -t "$SESSION:agents.1" \
    "claude --system-prompt \"\$(cat $REPO_ROOT/.agents/navigation.md)\"" Enter

# Split pane 0 vertically: Pane 2 (Control Agent)
tmux split-window -v -t "$SESSION:agents.0" -c "$REPO_ROOT"
tmux send-keys -t "$SESSION:agents.2" \
    "claude --system-prompt \"\$(cat $REPO_ROOT/.agents/control.md)\"" Enter

# Split pane 1 vertically: Pane 3 (Integration Agent)
tmux split-window -v -t "$SESSION:agents.1" -c "$REPO_ROOT"
tmux send-keys -t "$SESSION:agents.3" \
    "claude --system-prompt \"\$(cat $REPO_ROOT/.agents/integration.md)\"" Enter

# ── Layout: even 2x2 grid ────────────────────────────────────────────────────
tmux select-layout -t "$SESSION:agents" tiled

# ── Label panes (set pane titles) ────────────────────────────────────────────
tmux select-pane -t "$SESSION:agents.0" -T "PERCEPTION"
tmux select-pane -t "$SESSION:agents.1" -T "NAVIGATION"
tmux select-pane -t "$SESSION:agents.2" -T "CONTROL"
tmux select-pane -t "$SESSION:agents.3" -T "INTEGRATION"

# Enable pane titles in status bar
tmux set -t "$SESSION" pane-border-status top
tmux set -t "$SESSION" pane-border-format "#{pane_title}"

# ── Attach ────────────────────────────────────────────────────────────────────
info "Session '$SESSION' created with 4 agent panes:"
info "  [0] PERCEPTION  — OAK-D Lite + YOLOv8n + DepthAI v3"
info "  [1] NAVIGATION  — SLAM Toolbox + Nav2 + RPLIDAR A1M8"
info "  [2] CONTROL     — Teensy 4.1 + micro-ROS + PID + arm"
info "  [3] INTEGRATION — State machine + launch files + bringup"
info ""
info "Keybindings:"
info "  Ctrl+B, arrow keys  — Navigate between panes"
info "  Ctrl+B, z           — Zoom into/out of a pane"
info "  Ctrl+B, d           — Detach (reattach with: tmux attach -t $SESSION)"
echo ""

tmux attach -t "$SESSION"
