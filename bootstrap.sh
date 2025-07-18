#!/bin/bash

# TTRPG Assistant Bootstrap Script
# This script sets up the development environment and starts the MCP server

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Function to install Redis on different systems
install_redis() {
    local os=$(detect_os)
    
    print_status "Installing Redis for $os..."
    
    case $os in
        "linux")
            if command_exists apt-get; then
                print_status "Using apt-get to install Redis..."
                sudo apt-get update
                sudo apt-get install -y redis-server
            elif command_exists yum; then
                print_status "Using yum to install Redis..."
                sudo yum install -y redis
            elif command_exists dnf; then
                print_status "Using dnf to install Redis..."
                sudo dnf install -y redis
            elif command_exists pacman; then
                print_status "Using pacman to install Redis..."
                sudo pacman -S redis
            else
                print_error "Could not find a package manager to install Redis"
                print_error "Please install Redis manually: https://redis.io/download"
                exit 1
            fi
            ;;
        "macos")
            if command_exists brew; then
                print_status "Using Homebrew to install Redis..."
                brew install redis
            else
                print_error "Homebrew not found. Please install Homebrew first or install Redis manually"
                print_error "Homebrew: https://brew.sh/"
                print_error "Redis: https://redis.io/download"
                exit 1
            fi
            ;;
        "windows")
            print_warning "Windows detected. Please install Redis manually:"
            print_warning "1. Download Redis from: https://redis.io/download"
            print_warning "2. Or use WSL with Linux instructions"
            print_warning "3. Or use Docker: docker run -d -p 6379:6379 redis:latest"
            read -p "Press Enter after installing Redis, or Ctrl+C to exit..."
            ;;
        *)
            print_error "Unsupported operating system: $os"
            print_error "Please install Redis manually: https://redis.io/download"
            exit 1
            ;;
    esac
}

# Function to start Redis
start_redis() {
    print_status "Starting Redis server..."
    
    # Check if Redis is already running
    if command_exists redis-cli && redis-cli ping >/dev/null 2>&1; then
        print_success "Redis is already running"
        return 0
    fi
    
    # Try to start Redis
    if command_exists redis-server; then
        print_status "Starting Redis server in background..."
        redis-server --daemonize yes --logfile redis.log
        sleep 2
        
        # Verify Redis is running
        if redis-cli ping >/dev/null 2>&1; then
            print_success "Redis started successfully"
        else
            print_error "Failed to start Redis server"
            return 1
        fi
    else
        print_error "Redis server not found. Please install Redis first."
        return 1
    fi
}

# Function to setup Python virtual environment
setup_python_env() {
    print_status "Setting up Python virtual environment..."
    
    # Check if Python is available
    if ! command_exists python3 && ! command_exists python; then
        print_error "Python not found. Please install Python 3.8 or higher."
        exit 1
    fi
    
    # Use python3 if available, otherwise python
    PYTHON_CMD="python3"
    if ! command_exists python3; then
        PYTHON_CMD="python"
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    print_status "Found Python $PYTHON_VERSION"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        $PYTHON_CMD -m venv venv
    else
        print_status "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    print_status "Activating virtual environment..."
    source venv/bin/activate
    
    # Upgrade pip
    print_status "Upgrading pip..."
    python -m pip install --upgrade pip
    
    # Install requirements
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    print_success "Python environment setup complete"
}

# Function to run tests
run_tests() {
    print_status "Running basic tests..."
    
    if python test_basic.py; then
        print_success "All tests passed!"
    else
        print_error "Some tests failed. Please check the output above."
        return 1
    fi
}

# Function to start MCP server
start_mcp_server() {
    print_status "Starting TTRPG Assistant MCP Server..."
    print_status "The server will run until you stop it with Ctrl+C"
    print_status "You can now connect your MCP client to use the following tools:"
    print_status "  - search_rulebook: Search TTRPG rulebooks"
    print_status "  - manage_campaign: Manage campaign data"
    print_status "  - add_rulebook: Add new PDF rulebooks"
    echo
    
    # Start the server
    python main.py
}

# Main bootstrap function
main() {
    echo "=============================================="
    echo "  TTRPG Assistant MCP Server Bootstrap"
    echo "=============================================="
    echo
    
    # Check if we're in the right directory
    if [ ! -f "requirements.txt" ] || [ ! -f "main.py" ]; then
        print_error "Please run this script from the project root directory"
        exit 1
    fi
    
    # Step 1: Check for Redis
    print_status "Checking Redis installation..."
    if ! command_exists redis-server; then
        print_warning "Redis not found. Installing Redis..."
        install_redis
    else
        print_success "Redis is installed"
    fi
    
    # Step 2: Start Redis
    if ! start_redis; then
        print_error "Failed to start Redis. Cannot continue."
        exit 1
    fi
    
    # Step 3: Setup Python environment
    setup_python_env
    
    # Step 4: Run tests
    if ! run_tests; then
        print_warning "Tests failed, but continuing with server startup..."
    fi
    
    # Step 5: Display usage information
    echo
    print_success "Bootstrap completed successfully!"
    echo
    print_status "Quick usage guide:"
    print_status "  Add a rulebook: python cli.py add-rulebook 'path/to/book.pdf' 'Book Name' 'D&D 5e'"
    print_status "  Search: python cli.py search 'fireball spell'"
    print_status "  View stats: python cli.py stats"
    print_status "  Manage campaigns: python cli.py add-campaign-data 'campaign1' 'character' 'Gandalf'"
    echo
    
    # Step 6: Start MCP server
    start_mcp_server
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "TTRPG Assistant Bootstrap Script"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --no-server    Setup environment but don't start server"
        echo "  --test-only    Run tests only"
        echo
        echo "This script will:"
        echo "  1. Install Redis if not present"
        echo "  2. Start Redis server"
        echo "  3. Create Python virtual environment"
        echo "  4. Install dependencies"
        echo "  5. Run basic tests"
        echo "  6. Start the MCP server"
        exit 0
        ;;
    --no-server)
        main() {
            echo "=============================================="
            echo "  TTRPG Assistant Environment Setup"
            echo "=============================================="
            echo
            
            if [ ! -f "requirements.txt" ] || [ ! -f "main.py" ]; then
                print_error "Please run this script from the project root directory"
                exit 1
            fi
            
            print_status "Checking Redis installation..."
            if ! command_exists redis-server; then
                print_warning "Redis not found. Installing Redis..."
                install_redis
            else
                print_success "Redis is installed"
            fi
            
            if ! start_redis; then
                print_error "Failed to start Redis. Cannot continue."
                exit 1
            fi
            
            setup_python_env
            
            if ! run_tests; then
                print_warning "Tests failed. Please check the issues above."
            fi
            
            print_success "Environment setup completed!"
            print_status "To start the server later, run: python main.py"
        }
        ;;
    --test-only)
        main() {
            echo "=============================================="
            echo "  TTRPG Assistant Tests"
            echo "=============================================="
            echo
            
            if [ ! -f "requirements.txt" ] || [ ! -f "main.py" ]; then
                print_error "Please run this script from the project root directory"
                exit 1
            fi
            
            if [ -d "venv" ]; then
                source venv/bin/activate
            fi
            
            run_tests
        }
        ;;
esac

# Run main function
main "$@"