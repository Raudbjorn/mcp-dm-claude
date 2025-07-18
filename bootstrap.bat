@echo off
REM TTRPG Assistant Bootstrap Script for Windows
REM This script sets up the development environment and starts the MCP server

setlocal enabledelayedexpansion

REM Function to print colored output (limited colors in Windows)
echo ===============================================
echo   TTRPG Assistant MCP Server Bootstrap
echo ===============================================
echo.

REM Check if we're in the right directory
if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found. Please run this script from the project root directory.
    exit /b 1
)

if not exist "main.py" (
    echo ERROR: main.py not found. Please run this script from the project root directory.
    exit /b 1
)

REM Check for Python
echo [INFO] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.8 or higher.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [SUCCESS] Found Python %PYTHON_VERSION%

REM Check for Redis
echo [INFO] Checking Redis installation...
redis-server --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Redis not found. Please install Redis:
    echo   Option 1: Download from https://redis.io/download
    echo   Option 2: Use WSL with Linux instructions
    echo   Option 3: Use Docker: docker run -d -p 6379:6379 redis:latest
    echo.
    set /p choice="Press Enter after installing Redis, or 'q' to quit: "
    if /i "!choice!"=="q" exit /b 1
) else (
    echo [SUCCESS] Redis is installed
)

REM Check if Redis is running
echo [INFO] Checking if Redis is running...
redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Starting Redis server...
    start "Redis Server" redis-server
    echo Waiting for Redis to start...
    timeout /t 3 /nobreak >nul
    
    REM Check again
    redis-cli ping >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to start Redis. Please start Redis manually.
        echo Run: redis-server
        pause
        exit /b 1
    )
)
echo [SUCCESS] Redis is running

REM Create virtual environment if it doesn't exist
echo [INFO] Setting up Python virtual environment...
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
) else (
    echo [INFO] Virtual environment already exists
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [WARNING] Failed to upgrade pip, continuing anyway...
)

REM Install requirements
echo [INFO] Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install requirements
    pause
    exit /b 1
)

echo [SUCCESS] Python environment setup complete

REM Run tests
echo [INFO] Running basic tests...
python test_basic.py
if %errorlevel% neq 0 (
    echo [WARNING] Some tests failed, but continuing with server startup...
)

REM Display usage information
echo.
echo [SUCCESS] Bootstrap completed successfully!
echo.
echo [INFO] Quick usage guide:
echo   Add a rulebook: python cli.py add-rulebook "path\to\book.pdf" "Book Name" "D&D 5e"
echo   Search: python cli.py search "fireball spell"
echo   View stats: python cli.py stats
echo   Manage campaigns: python cli.py add-campaign-data "campaign1" "character" "Gandalf"
echo.

REM Check command line arguments
if "%1"=="--help" (
    echo TTRPG Assistant Bootstrap Script for Windows
    echo.
    echo Usage: bootstrap.bat [OPTIONS]
    echo.
    echo Options:
    echo   --help        Show this help message
    echo   --no-server   Setup environment but don't start server
    echo   --test-only   Run tests only
    echo.
    echo This script will:
    echo   1. Check for Python and Redis
    echo   2. Create Python virtual environment
    echo   3. Install dependencies
    echo   4. Run basic tests
    echo   5. Start the MCP server
    pause
    exit /b 0
)

if "%1"=="--no-server" (
    echo [SUCCESS] Environment setup completed!
    echo [INFO] To start the server later, run: python main.py
    pause
    exit /b 0
)

if "%1"=="--test-only" (
    echo [INFO] Tests completed
    pause
    exit /b 0
)

REM Start MCP server
echo [INFO] Starting TTRPG Assistant MCP Server...
echo [INFO] The server will run until you stop it with Ctrl+C
echo [INFO] You can now connect your MCP client to use the following tools:
echo [INFO]   - search_rulebook: Search TTRPG rulebooks
echo [INFO]   - manage_campaign: Manage campaign data
echo [INFO]   - add_rulebook: Add new PDF rulebooks
echo.

python main.py

echo.
echo [INFO] Server stopped
pause