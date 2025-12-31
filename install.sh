#!/bin/bash
# Installation script for DBTeamV2
# Created to automate the installation of all dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${GREEN}[DBTeamV2]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        OS=$DISTRIB_ID
        VERSION=$DISTRIB_RELEASE
    else
        OS=$(uname -s)
        VERSION=$(uname -r)
    fi
    
    echo "$OS"
}

# Function to check if running as root or with sudo
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        if ! command -v sudo &> /dev/null; then
            print_error "This script requires sudo privileges. Please install sudo or run as root."
            exit 1
        fi
        SUDO="sudo"
    else
        SUDO=""
    fi
}

# Function to install dependencies on Debian/Ubuntu
install_debian_ubuntu() {
    print_message "Installing dependencies for Debian/Ubuntu..."
    
    $SUDO apt-get update
    
    # Try to install dependencies
    if ! $SUDO apt-get install -y git redis-server libconfig8-dev libjansson-dev lua5.2 liblua5.2-dev lua-lgi glib-2.0 libnotify-dev libssl-dev libssl1.0.0 make libstdc++6 g++-4.9 unzip tmux; then
        print_warning "Some packages failed to install. Trying with additional repository..."
        $SUDO add-apt-repository ppa:ubuntu-toolchain-r/test -y || true
        $SUDO apt-get autoclean
        $SUDO apt-get update
        $SUDO apt-get install -y git redis-server libconfig8-dev libjansson-dev lua5.2 liblua5.2-dev lua-lgi glib-2.0 libnotify-dev libssl-dev libssl1.0.0 make libstdc++6 g++-4.9 unzip libreadline-gplv2-dev libreadline5-dev tmux
    fi
    
    print_message "System dependencies installed successfully!"
}

# Function to install dependencies on Arch
install_arch() {
    print_message "Installing dependencies for Arch Linux..."
    
    # Note: Arch package names may differ. Using pacman directly for basic packages.
    print_warning "Note: Some Debian package names may not exist in Arch. Installing available packages..."
    
    # Install basic packages with pacman (those that exist)
    $SUDO pacman -S --noconfirm --needed git redis lua52 tmux make gcc openssl glib2 libconfig jansson unzip
    
    # Install lua-lgi from AUR if yay is available
    if command -v yay &> /dev/null; then
        yay -S --noconfirm --needed lua-lgi
    elif command -v yaourt &> /dev/null; then
        yaourt -S --noconfirm lua-lgi
    else
        print_warning "AUR helper (yay/yaourt) not found. You may need to manually install lua-lgi from AUR."
    fi
    
    print_message "System dependencies installed successfully!"
}

# Function to install dependencies on Fedora
install_fedora() {
    print_message "Installing dependencies for Fedora..."
    
    # Fedora uses different package names than Debian
    # Install all packages including lua-devel in one command
    $SUDO dnf install -y git redis lua lua-devel tmux make gcc openssl-devel glib2-devel libconfig-devel jansson-devel unzip libnotify-devel readline-devel
    
    print_message "System dependencies installed successfully!"
}

# Function to install Python dependencies
install_python_deps() {
    print_message "Installing Python dependencies for python_api..."
    
    if [ ! -d "python_api" ]; then
        print_warning "python_api directory not found. Skipping Python dependencies."
        return
    fi
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3 first."
        return
    fi
    
    if ! command -v pip3 &> /dev/null; then
        print_warning "pip3 is not installed. Installing pip3..."
        case $OS in
            ubuntu|debian)
                $SUDO apt-get install -y python3-pip
                ;;
            arch)
                $SUDO pacman -S --noconfirm python-pip
                ;;
            fedora)
                $SUDO dnf install -y python3-pip
                ;;
        esac
    fi
    
    print_message "Installing Python packages from requirements.txt..."
    pip3 install --user -r python_api/requirements.txt
    
    print_message "Python dependencies installed successfully!"
}

# Main installation function
main() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════╗"
    echo "║   DBTeamV2 Automated Installation Script  ║"
    echo "╔═══════════════════════════════════════════╗"
    echo -e "${NC}"
    
    # Check sudo
    check_sudo
    
    # Detect OS
    OS=$(detect_os)
    print_message "Detected OS: $OS"
    
    # Install system dependencies based on OS
    case $OS in
        ubuntu|debian)
            install_debian_ubuntu
            ;;
        arch|manjaro)
            install_arch
            ;;
        fedora)
            install_fedora
            ;;
        *)
            print_error "Unsupported operating system: $OS"
            print_message "Please install dependencies manually according to README.md"
            exit 1
            ;;
    esac
    
    # Check if launch.sh exists
    if [ ! -f "launch.sh" ]; then
        print_error "launch.sh not found. Please run this script from the DBTeamV2 directory."
        exit 1
    fi
    
    # Make launch.sh executable if it isn't
    chmod +x launch.sh
    
    # Run launch.sh install
    print_message "Configuring DBTeamV2 (installing Lua dependencies and telegram-cli)..."
    ./launch.sh install
    
    # Ask about Python dependencies
    echo ""
    read -p "Do you want to install Python API dependencies? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_python_deps
    fi
    
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Installation completed successfully!     ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
    echo ""
    print_message "You can now run './launch.sh' to start the bot."
    print_message "For more information, see README.md"
}

# Run main function
main
