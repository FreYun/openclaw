#!/usr/bin/env bash

# ==============================================================================
# AI Development Tools Complete Installer
# Installs: Node.js, npm, Claude Code, Codex CLI
# Platform: macOS, Linux, Windows WSL
# Version: 3.4.0 (Simplified, No Redundant Checks)
# ==============================================================================

set -euo pipefail

# Script Constants
readonly SCRIPT_VERSION="3.4.0"
readonly NVM_VERSION="v0.40.3"
readonly NODE_VERSION="24"
readonly MIN_NODE_VERSION="18.0.0"
readonly MIN_NPM_VERSION="9.0.0"

# npm Package Configuration
readonly CLAUDE_NPM_PACKAGE="@anthropic-ai/claude-code"
readonly CLAUDE_CMD="claude"
readonly CLAUDE_DISPLAY_NAME="Claude Code"

readonly CODEX_NPM_PACKAGE="@openai/codex"
readonly CODEX_CMD="codex"
readonly CODEX_DISPLAY_NAME="Codex CLI"

# Installation Choices (set by user)
INSTALL_CLAUDE=false
INSTALL_CODEX=false

# ANSI Color Codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly NC='\033[0m'

# ============================================
# Utility Functions
# ============================================

print_banner() {
    clear
    echo -e "${CYAN}"
    echo "========================================"
    echo ""
    echo "  AI Development Tools Installer"
    echo "  Version: ${SCRIPT_VERSION}"
    echo ""
    echo "  Installs: Node.js, Claude Code, Codex CLI"
    echo "  Platform: macOS, Linux, WSL"
    echo ""
    echo "========================================"
    echo -e "${NC}"
}

print_info() {
    echo -e "${WHITE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_section() {
    echo ""
    echo -e "${MAGENTA}========================================${NC}"
    echo -e "${MAGENTA}  $1${NC}"
    echo -e "${MAGENTA}========================================${NC}"
    echo ""
}

# ============================================
# User Selection Menu
# ============================================

show_install_menu() {
    clear
    echo -e "${CYAN}"
    echo "========================================"
    echo ""
    echo "  AI Development Tools Installer"
    echo "  Version: ${SCRIPT_VERSION}"
    echo ""
    echo "========================================"
    echo -e "${NC}"
    echo ""
    echo -e "${WHITE}Select tools to install:${NC}"
    echo ""
    echo -e "  ${GREEN}1${NC}) Claude Code only"
    echo -e "  ${GREEN}2${NC}) Codex CLI only"
    echo -e "  ${GREEN}3${NC}) Install both (Recommended)"
    echo -e "  ${GREEN}q${NC}) Quit"
    echo ""

    # Use /dev/tty to read input, supports curl | bash
    if [ -t 0 ]; then
        read -p "Choose [1-3]: " -r choice
    else
        read -p "Choose [1-3]: " -r choice < /dev/tty
    fi

    case "$choice" in
        1)
            INSTALL_CLAUDE=true
            INSTALL_CODEX=false
            print_success "Will install: Claude Code"
            ;;
        2)
            INSTALL_CLAUDE=false
            INSTALL_CODEX=true
            print_success "Will install: Codex CLI"
            ;;
        3)
            INSTALL_CLAUDE=true
            INSTALL_CODEX=true
            print_success "Will install: Claude Code + Codex CLI"
            ;;
        q|Q)
            print_info "Installation cancelled"
            exit 0
            ;;
        *)
            print_error "Invalid selection"
            echo ""
            read -p "Press Enter to try again..." -r
            show_install_menu
            return
            ;;
    esac
}

# ============================================
# System Detection
# ============================================

detect_os() {
    if grep -qEi "(Microsoft|WSL)" /proc/version 2>/dev/null; then
        echo "wsl"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

detect_arch() {
    local arch=$(uname -m)
    case "$arch" in
        x86_64|amd64) echo "x64" ;;
        arm64|aarch64) echo "arm64" ;;
        *) echo "unknown" ;;
    esac
}

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

get_shell_config() {
    local os_type=${1:-"unknown"}

    # Check SHELL environment variable first
    if [[ -n "${SHELL:-}" ]]; then
        if [[ "$SHELL" == *"zsh"* ]]; then
            echo "$HOME/.zshrc"
            return 0
        elif [[ "$SHELL" == *"bash"* ]]; then
            if [[ "$os_type" == "macos" ]]; then
                echo "$HOME/.bash_profile"
            else
                echo "$HOME/.bashrc"
            fi
            return 0
        fi
    fi

    # Detect based on OS type
    if [[ "$os_type" == "macos" ]]; then
        if [ -f "$HOME/.zshrc" ]; then
            echo "$HOME/.zshrc"
        elif [ -f "$HOME/.bash_profile" ]; then
            echo "$HOME/.bash_profile"
        else
            echo "$HOME/.zshrc"  # default
        fi
    else
        if [ -f "$HOME/.zshrc" ]; then
            echo "$HOME/.zshrc"
        elif [ -f "$HOME/.bashrc" ]; then
            echo "$HOME/.bashrc"
        else
            echo "$HOME/.bashrc"  # default
        fi
    fi
}

# ============================================
# Version Checks
# ============================================

version_compare() {
    local version1=${1#v}
    local version2=${2#v}

    if printf '%s\n%s\n' "$version2" "$version1" | sort -V -C 2>/dev/null; then
        return 0  # version1 >= version2
    else
        return 1  # version1 < version2
    fi
}

check_node_installed() {
    if ! command -v node &> /dev/null; then
        return 1
    fi

    local current_version=$(node -v 2>/dev/null | sed 's/v//')
    print_info "Current Node.js version: v$current_version"

    if version_compare "$current_version" "$MIN_NODE_VERSION"; then
        print_success "Node.js version meets requirements (>= $MIN_NODE_VERSION)"
        return 0
    else
        print_warning "Node.js version too old (requires >= $MIN_NODE_VERSION)"
        return 1
    fi
}

check_npm_installed() {
    if ! command -v npm &> /dev/null; then
        print_error "npm not installed"
        return 1
    fi

    local current_version=$(npm -v 2>/dev/null)
    print_info "Current npm version: v$current_version"
    print_success "npm is available"
    return 0
}

check_git_installed() {
    if ! command -v git &> /dev/null; then
        print_warning "Git not found"
        print_info "Git is recommended for development"
        echo ""

        local os_type=$(detect_os)
        case "$os_type" in
            macos)
                # Try to install with Homebrew
                if command -v brew &> /dev/null; then
                    print_step "Installing Git using Homebrew..."
                    if brew install git; then
                        print_success "Git installed successfully"
                        return 0
                    fi
                else
                    print_info "Install Homebrew first: https://brew.sh"
                fi
                ;;
            linux|wsl)
                # Try apt-get
                if command -v apt-get &> /dev/null; then
                    print_step "Installing Git using apt-get..."
                    if sudo apt-get update && sudo apt-get install -y git; then
                        print_success "Git installed successfully"
                        return 0
                    fi
                fi
                ;;
        esac

        print_info "Please install Git manually: https://git-scm.com/"
        return 1
    fi

    local git_version=$(git --version 2>/dev/null)
    print_success "$git_version"
    return 0
}

# ============================================
# Dependency Installation
# ============================================

install_with_nvm() {
    print_step "Installing Node.js using nvm..."

    # Check if nvm is already installed
    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        print_info "nvm already installed"
        . "$HOME/.nvm/nvm.sh"
    else
        local os_type=$(detect_os)
        local shell_config
        shell_config=$(get_shell_config "$os_type")

        if [ -z "$shell_config" ]; then
            shell_config="$HOME/.bashrc"
        fi

        # Check if shell config already has nvm (avoid duplicate install)
        if [ -f "$shell_config" ] && grep -q "NVM_DIR" "$shell_config" 2>/dev/null; then
            print_warning "Detected nvm config in ${shell_config}"
            print_info "Attempting to load nvm..."
            export NVM_DIR="$HOME/.nvm"
            [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

            if command -v nvm &> /dev/null; then
                print_success "nvm loaded successfully"
            else
                print_error "Failed to load nvm, please check configuration manually"
                return 1
            fi
        else
            print_step "Downloading and installing nvm..."
            print_warning "nvm installer will modify your shell config: ${shell_config}"

            # Ensure shell config file ends with a newline to prevent nvm config from being appended to the last line
            if [ -f "$shell_config" ]; then
                # Check if file ends with newline, if not, add one
                if [ -s "$shell_config" ] && [ "$(tail -c 1 "$shell_config" | wc -l)" -eq 0 ]; then
                    echo "" >> "$shell_config"
                    print_info "Added newline to end of ${shell_config}"
                fi
            fi

            if curl -o- "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_VERSION}/install.sh" | bash; then
                export NVM_DIR="$HOME/.nvm"
                [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
                print_success "nvm installation complete"
                print_info "Config file updated: ${shell_config}"
            else
                print_error "nvm installation failed"
                return 1
            fi
        fi
    fi

    # Install Node.js
    print_step "Installing Node.js ${NODE_VERSION}..."
    if nvm install ${NODE_VERSION} && nvm use ${NODE_VERSION}; then
        print_success "Node.js $(node -v) installed successfully"
        print_success "npm v$(npm -v) installed successfully"
        return 0
    else
        print_error "Node.js installation failed"
        return 1
    fi
}

install_macos_deps() {
    print_step "Installing macOS dependencies..."

    if command -v brew &> /dev/null; then
        print_success "Detected Homebrew, using brew to install Node.js"
        print_info "brew will not modify your shell config files"

        if brew install node; then
            print_success "Node.js installation complete"
            print_info "Homebrew automatically configured PATH"
            return 0
        else
            print_warning "Homebrew installation failed, trying nvm"
            install_with_nvm
        fi
    else
        print_warning "Homebrew not detected, using nvm"
        print_info "Recommend installing Homebrew for better package management"
        echo ""
        print_info "Continue with nvm? (nvm will modify your shell config)"
        read -p "Continue? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_with_nvm
        else
            print_warning "Installation cancelled"
            print_info "You can manually download from https://nodejs.org/"
            return 1
        fi
    fi
}

install_linux_deps() {
    local distro=$(detect_distro)
    print_info "Linux distribution: $distro"
    install_with_nvm
}

show_upgrade_instructions() {
    local os_type=$1
    local current_version=$2

    echo ""
    print_warning "Node.js version too old (current: v$current_version, requires: >= $MIN_NODE_VERSION)"
    print_info "Recommend manually upgrading Node.js:"
    echo ""

    case "$os_type" in
        macos)
            echo "  Using Homebrew:"
            echo "    $ brew upgrade node"
            echo ""
            echo "  Or using nvm:"
            echo "    $ nvm install --lts"
            ;;
        linux|wsl)
            echo "  Using nvm:"
            echo "    $ nvm install --lts"
            echo "    $ nvm use --lts"
            ;;
    esac
    echo ""
    print_info "Script will continue using current version to install AI tools"
    echo ""
}

install_dependencies() {
    local os_type=$(detect_os)

    print_step "Detecting system environment..."
    print_info "Operating system: $os_type"
    print_info "Architecture: $(detect_arch)"
    echo ""

    # Check if Node.js is already installed
    if command -v node &> /dev/null; then
        local current_version=$(node -v 2>/dev/null | sed 's/v//')
        print_success "Node.js already installed: v$current_version"

        # Check version
        if ! version_compare "$current_version" "$MIN_NODE_VERSION"; then
            show_upgrade_instructions "$os_type" "$current_version"
        fi
        return 0
    fi

    # Not installed, proceed with installation
    print_warning "Node.js not installed"
    echo ""

    case "$os_type" in
        macos)
            install_macos_deps
            ;;
        linux|wsl)
            install_linux_deps
            ;;
        *)
            print_error "Unsupported operating system: $os_type"
            exit 1
            ;;
    esac
}

# ============================================
# PATH Configuration Help
# ============================================

check_path_exists() {
    local path_to_check=$1
    if [[ ":$PATH:" == *":$path_to_check:"* ]]; then
        return 0  # path exists
    else
        return 1  # path doesn't exist
    fi
}

check_config_has_npm_path() {
    local config_file=$1
    local npm_bin=$2

    # If config file doesn't exist, return 1 (not configured)
    if [ ! -f "$config_file" ]; then
        return 1
    fi

    # Check if file contains npm path config
    if grep -q "export PATH.*${npm_bin}" "$config_file" 2>/dev/null || \
       grep -q "${npm_bin}.*PATH" "$config_file" 2>/dev/null; then
        return 0  # configured
    else
        return 1  # not configured
    fi
}

show_path_config_help() {
    local os_type=$(detect_os)
    local npm_bin=$(npm bin -g 2>/dev/null || echo "")

    # Validate path
    if [ -z "$npm_bin" ] || [ "$npm_bin" = "undefined" ] || [ ! -d "$npm_bin" ]; then
        echo ""
        print_info "Please check npm global installation path, or reopen terminal"
        return 0
    fi

    # Check if PATH contains npm bin path
    if check_path_exists "$npm_bin"; then
        echo ""
        print_success "npm global path already in PATH"
        return 0
    fi

    local shell_config
    shell_config=$(get_shell_config "$os_type")

    # Ensure shell_config is not empty
    if [ -z "$shell_config" ]; then
        shell_config="$HOME/.bashrc"
    fi

    # Check if config file already has npm path config
    if check_config_has_npm_path "$shell_config" "$npm_bin"; then
        echo ""
        print_info "Detected npm path configured in ${shell_config}"
        print_warning "But current session PATH doesn't contain it"
        echo ""
        print_info "Please run the following command to reload config:"
        echo -e "  ${CYAN}\$ source ${shell_config}${NC}"
        echo ""
        print_info "Or reopen terminal"
        return 0
    fi

    echo ""
    print_info "npm global bin path: $npm_bin"
    echo ""
    print_warning "Need to add npm global path to PATH environment variable"
    echo ""
    print_info "Please manually add the following config:"

    echo ""
    echo -e "  ${CYAN}# 1. Edit config file${NC}"
    echo -e "  ${CYAN}\$ vim ${shell_config}${NC}"
    echo ""
    echo -e "  ${CYAN}# 2. Add this line at the end:${NC}"
    echo -e "  ${GREEN}export PATH=\"${npm_bin}:\$PATH\"${NC}"
    echo ""
    echo -e "  ${CYAN}# 3. Save and reload config:${NC}"
    echo -e "  ${CYAN}\$ source ${shell_config}${NC}"
    echo ""

    # Only add to current session if not in PATH
    if ! check_path_exists "$npm_bin"; then
        export PATH="$npm_bin:$PATH"
        print_info "Temporarily added to current session (will expire after terminal restart)"
    fi
}

# ============================================
# npm Package Installation (Generic)
# ============================================

install_npm_package() {
    local package_name=$1
    local command_name=$2
    local display_name=$3

    print_section "Installing $display_name"

    # Check npm availability
    if ! command -v npm &> /dev/null; then
        print_error "npm not available, cannot install $display_name"
        return 1
    fi

    # Check if command already exists (simple and fast)
    if command -v "$command_name" &> /dev/null; then
        local version=$($command_name --version 2>/dev/null || echo "unknown")
        print_success "$display_name already installed (version: $version)"
        print_info "Skipping installation"
        return 0
    fi

    # Command not found, install directly (no slow npm checks)
    print_step "Installing $display_name..."
    print_info "This may take a few minutes..."
    echo ""

    if npm install -g "$package_name" --loglevel=warn 2>&1; then
        sleep 1

        # Verify installation
        if command -v "$command_name" &> /dev/null; then
            local version=$($command_name --version 2>/dev/null || echo "installed")
            print_success "$display_name successfully installed (version: $version)"
            return 0
        else
            print_warning "$display_name installed, but $command_name command not found"
            show_path_config_help
            return 0
        fi
    else
        print_error "$display_name installation failed"
        print_info "You can try manually: npm install -g $package_name"
        return 1
    fi
}

# ============================================
# Environment Verification
# ============================================

verify_installation() {
    print_banner
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Installation Complete${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    echo -e "${WHITE}Installed tools:${NC}"
    echo ""

    # Node.js
    if command -v node &> /dev/null; then
        print_success "Node.js: $(node -v)"
    else
        print_error "Node.js not installed"
    fi

    # npm
    if command -v npm &> /dev/null; then
        print_success "npm: v$(npm -v)"
    else
        print_error "npm not installed"
    fi

    # Git
    if command -v git &> /dev/null; then
        local git_version=$(git --version 2>/dev/null)
        print_success "$git_version"
    else
        print_warning "Git not installed (recommended)"
    fi

    # Claude Code
    if command -v claude &> /dev/null; then
        local version=$(claude --version 2>/dev/null || echo "unknown")
        print_success "Claude Code: $version"
    else
        print_warning "Claude Code not installed"
    fi

    # Codex CLI
    if command -v codex &> /dev/null; then
        local version=$(codex --version 2>/dev/null || echo "installed")
        print_success "Codex CLI: $version"
    else
        print_warning "Codex CLI not installed"
    fi

    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  Usage Instructions${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""

    print_info "Claude Code usage:"
    echo "  $ claude --help"
    echo "  $ claude \"your question\""
    echo ""

    # If nvm was used, show reload instructions
    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        local os_type=$(detect_os)
        local shell_config
        shell_config=$(get_shell_config "$os_type")

        # Ensure shell_config is not empty
        if [ -z "$shell_config" ]; then
            shell_config="~/.bashrc"
        fi

        echo ""
        print_warning "IMPORTANT:"
        echo "  If commands don't work, please run:"
        echo ""
        echo -e "  ${CYAN}\$ source ${shell_config}${NC}"
        echo ""
        echo "  Or reopen terminal"
    fi

    echo ""
}

# ============================================
# Network Check
# ============================================

check_network() {
    if ping -c 1 -W 2 www.baidu.com > /dev/null 2>&1 || \
       ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
        print_success "Network connection OK"
        return 0
    else
        print_warning "Network connection may have issues, continuing anyway..."
        return 1
    fi
}

# ============================================
# Main Function
# ============================================

main() {
    # Show selection menu
    show_install_menu

    echo ""
    sleep 1
    print_banner

    # Check network
    check_network

    echo ""

    # Check git (recommended)
    print_step "Checking Git..."
    check_git_installed

    echo ""
    print_info "This script will install:"
    echo "  1. Node.js (>= ${MIN_NODE_VERSION})"
    echo "  2. npm (>= ${MIN_NPM_VERSION})"
    if [ "$INSTALL_CLAUDE" = true ]; then
        echo "  3. Claude Code"
    fi
    if [ "$INSTALL_CODEX" = true ]; then
        echo "  4. Codex CLI"
    fi
    echo ""
    print_step "Starting installation..."
    echo ""

    # 1. Install Node.js and npm
    if ! install_dependencies; then
        print_error "Node.js installation failed, cannot continue"
        exit 1
    fi

    # 2. Install tools based on user selection
    if [ "$INSTALL_CLAUDE" = true ]; then
        install_npm_package "$CLAUDE_NPM_PACKAGE" "$CLAUDE_CMD" "$CLAUDE_DISPLAY_NAME"
    fi

    if [ "$INSTALL_CODEX" = true ]; then
        install_npm_package "$CODEX_NPM_PACKAGE" "$CODEX_CMD" "$CODEX_DISPLAY_NAME"
    fi

    # 3. Show installation results
    echo ""
    sleep 1
    verify_installation
}

# Run main function
main "$@"
