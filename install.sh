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
    echo -e "${RED}✗ Python 3 não encontrado.${NC}"
    echo "Instale o Python 3.8+ primeiro: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✓${NC} Python ${PYTHON_VERSION} encontrado"

# ─── Check Git ───
if ! command -v git &> /dev/null; then
    echo -e "${RED}✗ Git não encontrado.${NC}"
    echo "Instale o Git primeiro: https://git-scm.com/downloads"
    exit 1
fi
echo -e "${GREEN}✓${NC} Git encontrado"

# ─── Clone or update repository ───
if [ -d "$INSTALL_DIR" ]; then
    if git -C "$INSTALL_DIR" rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠${NC} MyFi já existe em $INSTALL_DIR. A atualizar..."
        cd "$INSTALL_DIR"
        if ! git pull --quiet; then
            echo -e "${YELLOW}⚠${NC} Não foi possível atualizar. A recriar..."
            cd "$HOME"
            rm -rf "$INSTALL_DIR"
            git clone --quiet "$REPO_URL" "$INSTALL_DIR"
            cd "$INSTALL_DIR"
        fi
    else
        echo -e "${YELLOW}⚠${NC} A pasta $INSTALL_DIR existe mas não é um repositório git. A recriar..."
        rm -rf "$INSTALL_DIR"
        git clone --quiet "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
else
    echo -e "${CYAN}↓${NC} A clonar MyFi..."
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ─── Create virtual environment ───
if [ ! -d "venv" ]; then
    echo -e "${CYAN}⚙${NC} A criar ambiente virtual..."
    python3 -m venv venv
fi

# ─── Activate and install ───
source venv/bin/activate
echo -e "${CYAN}⚙${NC} A instalar dependências..."
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
echo -e "${GREEN}✓ MyFi instalado com sucesso!${NC}"
echo ""
echo -e "Comando disponível: ${CYAN}myfi${NC}"
echo ""
echo -e "${YELLOW}🚀 A executar o assistente de configuração...${NC}"
echo ""

# ─── Run setup wizard ───
myfi setup

echo ""
echo -e "${GREEN}✅ Pronto! O MyFi está configurado.${NC}"
echo -e "Comandos úteis:"
echo -e "  ${CYAN}myfi scan${NC}       — Descobrir dispositivos na rede"
echo -e "  ${CYAN}myfi monitor${NC}    — Monitorizar tráfego"
echo -e "  ${CYAN}myfi limit${NC}      — Gerir limites de consumo"
echo -e "  ${CYAN}myfi web${NC}        — Iniciar interface web"
echo -e "  ${CYAN}myfi --help${NC}     — Ver todos os comandos"
