@echo off
REM Quick start script for VibeAnalytix development on Windows

echo.
echo 🚀 VibeAnalytix Setup
echo ====================
echo.

REM Check for Docker
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Docker is not installed or not in PATH
    exit /b 1
)

REM Check for Docker Compose
where docker-compose >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Docker Compose is not installed or not in PATH
    exit /b 1
)

REM Check if .env exists
if not exist .env (
    echo 📝 Creating .env file from .env.example...
    copy .env.example .env
    echo.
    echo ⚠️  Update .env with your OpenAI API key before continuing
    exit /b 1
)

REM Start services
echo 🐳 Starting Docker Compose services...
docker-compose up -d

REM Wait for services to be healthy
echo ⏳ Waiting for services to be healthy...
timeout /t 5 /nobreak

REM Check if services are running
docker-compose ps | findstr "Up" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✅ Services started successfully!
    echo.
    echo 📍 Access points:
    echo    Frontend: http://localhost:3000
    echo    API: http://localhost:8000
    echo    API Docs: http://localhost:8000/docs
    echo.
    echo 🎯 Next steps:
    echo    1. Open http://localhost:3000 in your browser
    echo    2. Create an account
    echo    3. Submit a GitHub repository or ZIP file
    echo.
    echo 📊 Monitor progress:
    echo    docker-compose logs -f api
    echo    docker-compose logs -f worker
) else (
    echo ❌ Failed to start services
    docker-compose logs
    exit /b 1
)
