set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

REPO_URL="https://github.com/lioexp/myfi.git"
INSTALL_DIR="$HOME/myfi"

echo -e "${CYAN}"
echo "   ███╗   ███╗██╗   ██╗███████╗██╗"
echo "   ████╗ ████║╚██╗ ██╔╝██╔════╝██║"
echo "   ██╔████╔██║ ╚████╔╝ █████╗  ██║"
echo "   ██║╚██╔╝██║  ╚██╔╝  ██╔══╝  ██║"
echo "   ██║ ╚═╝ ██║   ██║   ██║     ██║"
echo "   ╚═╝     ╚═╝   ╚═╝   ╚═╝     ╚═╝"
echo -e "${NC}"
echo -e "${CYAN}MyFi Installer${NC}"
echo ""

# ─── Check Python ───
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found.${NC}"
    echo "Please install Python 3.8+ first: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✓${NC} Python ${PYTHON_VERSION} found"

# ─── Check Git ───
if ! command -v git &> /dev/null; then
    echo -e "${RED}✗ Git not found.${NC}"
    echo "Please install Git first: https://git-scm.com/downloads"
    exit 1
fi
echo -e "${GREEN}✓${NC} Git found"

# ─── Clone or update repository ───
if [ -d "$INSTALL_DIR" ]; then
    if git -C "$INSTALL_DIR" rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠${NC} MyFi already exists at $INSTALL_DIR. Updating..."
        cd "$INSTALL_DIR"
        if ! git pull --quiet; then
            echo -e "${YELLOW}⚠${NC} Could not update. Recreating..."
            cd "$HOME"
            rm -rf "$INSTALL_DIR"
            git clone --quiet "$REPO_URL" "$INSTALL_DIR"
            cd "$INSTALL_DIR"
        fi
    else
        echo -e "${YELLOW}⚠${NC} $INSTALL_DIR already exists but is not a git repository. Recreating..."
        rm -rf "$INSTALL_DIR"
        git clone --quiet "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
else
    echo -e "${CYAN}↓${NC} Cloning MyFi..."
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ─── Create virtual environment ───
if [ ! -d "venv" ]; then
    echo -e "${CYAN}⚙${NC} Creating virtual environment..."
    python3 -m venv venv
fi

# ─── Activate and install ───
source venv/bin/activate
echo -e "${CYAN}⚙${NC} Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet -e .

# ─── Create symlink for global access ───
SYMLINK_DIR="$HOME/.local/bin"
mkdir -p "$SYMLINK_DIR"
ln -sf "$INSTALL_DIR/venv/bin/myfi" "$SYMLINK_DIR/myfi"

# Add to PATH if not already there
if [[ ":$PATH:" != *":$SYMLINK_DIR:"* ]]; then
    echo "export PATH=\"$SYMLINK_DIR:\$PATH\"" >> "$HOME/.bashrc"
    echo "export PATH=\"$SYMLINK_DIR:\$PATH\"" >> "$HOME/.zshrc" 2>/dev/null || true
    export PATH="$SYMLINK_DIR:$PATH"
fi

echo ""
echo -e "${GREEN}✓ MyFi installed successfully!${NC}"
echo ""
echo -e "Command available: ${CYAN}myfi${NC}"
echo ""
echo -e "${YELLOW}🚀 Running the setup wizard...${NC}"
echo ""

# ─── Run setup wizard ───
myfi setup

echo ""
echo -e "${GREEN}✅ Done! MyFi is now configured.${NC}"
echo -e "Useful commands:"
echo -e "  ${CYAN}myfi scan${NC}       — Discover devices on your network"
echo -e "  ${CYAN}myfi monitor${NC}    — Monitor traffic"
echo -e "  ${CYAN}myfi limit${NC}      — Manage usage limits"
echo -e "  ${CYAN}myfi web${NC}        — Start the web interface"
echo -e "  ${CYAN}myfi --help${NC}     — Show all commands"
