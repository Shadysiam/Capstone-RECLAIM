#!/usr/bin/env bash
# setup.sh — One-time setup for RECLAIM multi-agent development environment
# Installs tmux, configures SSH key auth to MIC-711, creates remote workspace
set -euo pipefail

MIC_HOST="192.168.2.2"
MIC_USER="mic-711"
MIC_PASS="mic-711"
SSH_KEY="$HOME/.ssh/id_ed25519_mic711"
SSH_CONFIG="$HOME/.ssh/config"
REMOTE_WS="~/reclaim_ws"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[x]${NC} $1"; }

# ── 1. Install tmux via Homebrew ──────────────────────────────────────────────
if command -v tmux &>/dev/null; then
    info "tmux already installed: $(tmux -V)"
else
    info "Installing tmux via Homebrew..."
    if ! command -v brew &>/dev/null; then
        error "Homebrew not found. Install it first: https://brew.sh"
        exit 1
    fi
    brew install tmux
    info "tmux installed: $(tmux -V)"
fi

# ── 2. Generate SSH key ──────────────────────────────────────────────────────
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if [ -f "$SSH_KEY" ]; then
    info "SSH key already exists at $SSH_KEY"
else
    info "Generating ED25519 SSH key for MIC-711..."
    ssh-keygen -t ed25519 -f "$SSH_KEY" -N "" -C "reclaim-dev@$(hostname)"
    info "Key generated at $SSH_KEY"
fi

# ── 3. Copy SSH key to MIC-711 ───────────────────────────────────────────────
info "Copying SSH key to ${MIC_USER}@${MIC_HOST}..."
info "You may be prompted for the password: ${MIC_PASS}"

if command -v sshpass &>/dev/null; then
    sshpass -p "$MIC_PASS" ssh-copy-id -i "$SSH_KEY.pub" -o StrictHostKeyChecking=no "${MIC_USER}@${MIC_HOST}"
else
    warn "sshpass not installed. You can install it with: brew install sshpass"
    warn "Falling back to manual ssh-copy-id (you'll type the password)..."
    ssh-copy-id -i "$SSH_KEY.pub" -o StrictHostKeyChecking=no "${MIC_USER}@${MIC_HOST}"
fi

# ── 4. Add SSH config alias ──────────────────────────────────────────────────
if grep -q "^Host mic$" "$SSH_CONFIG" 2>/dev/null; then
    info "SSH alias 'mic' already exists in $SSH_CONFIG"
else
    info "Adding SSH alias 'mic' to $SSH_CONFIG..."
    cat >> "$SSH_CONFIG" <<EOF

# RECLAIM MIC-711 (Jetson Orin NX)
Host mic
    HostName ${MIC_HOST}
    User ${MIC_USER}
    IdentityFile ${SSH_KEY}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
    ServerAliveInterval 15
    ServerAliveCountMax 3
    ConnectTimeout 10
EOF
    chmod 600 "$SSH_CONFIG"
    info "SSH alias added. You can now use: ssh mic"
fi

# ── 5. Test SSH connection ────────────────────────────────────────────────────
info "Testing SSH connection..."
if ssh mic "echo 'Connection OK'" 2>/dev/null; then
    info "SSH connection to MIC-711 successful (no password needed)"
else
    error "SSH connection failed. Check that the MIC-711 is powered on and connected via the GL.iNet Mango router."
    error "Expected IP: ${MIC_HOST}"
    exit 1
fi

# ── 6. Create remote workspace ───────────────────────────────────────────────
info "Creating remote workspace on MIC-711..."
ssh mic <<'REMOTE'
    mkdir -p ~/reclaim_ws/src
    echo "Remote workspace ready at ~/reclaim_ws"
    # Show system info for verification
    echo "---"
    echo "Hostname: $(hostname)"
    echo "Arch: $(uname -m)"
    echo "Ubuntu: $(lsb_release -rs 2>/dev/null || echo 'unknown')"
    echo "ROS2: $(printenv ROS_DISTRO 2>/dev/null || echo 'not sourced')"
    echo "Free disk: $(df -h ~ | tail -1 | awk '{print $4}')"
REMOTE

# ── 7. Verify rsync works ────────────────────────────────────────────────────
info "Testing rsync connectivity..."
TMPFILE=$(mktemp)
echo "rsync test $(date)" > "$TMPFILE"
if rsync -avz "$TMPFILE" mic:/tmp/rsync_test 2>/dev/null; then
    info "rsync working correctly"
    ssh mic "rm -f /tmp/rsync_test" 2>/dev/null
else
    warn "rsync test failed. Make sure rsync is installed on the MIC-711: sudo apt install rsync"
fi
rm -f "$TMPFILE"

# ── 8. Install Claude Code if needed ─────────────────────────────────────────
if command -v claude &>/dev/null; then
    info "Claude Code already installed: $(claude --version 2>/dev/null || echo 'available')"
else
    warn "Claude Code (claude) not found in PATH."
    warn "Install it from: https://docs.anthropic.com/en/docs/claude-code"
    warn "Or run: npm install -g @anthropic-ai/claude-code"
fi

echo ""
info "Setup complete. Run ./launch-agents.sh to start the multi-agent TMUX session."
