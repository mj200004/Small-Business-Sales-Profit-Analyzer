@echo off
REM Business Analyzer - Docker Deployment Script for Windows

setlocal enabledelayedexpansion

REM Configuration
set IMAGE_NAME=business-analyzer
set CONTAINER_NAME=business-analyzer-app
set PORT=8501

echo ========================================
echo Business Analyzer - Deployment Script
echo ========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not installed
    echo Please install Docker Desktop: https://docs.docker.com/desktop/install/windows-install/
    exit /b 1
)
echo [OK] Docker is installed

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running
    echo Please start Docker Desktop and try again
    exit /b 1
)
echo [OK] Docker is running
echo.

REM Parse command
if "%1"=="" goto usage
if "%1"=="build" goto build
if "%1"=="run" goto run
if "%1"=="deploy" goto deploy
if "%1"=="logs" goto logs
if "%1"=="stop" goto stop
if "%1"=="start" goto start
if "%1"=="restart" goto restart
if "%1"=="clean" goto clean
if "%1"=="status" goto status
goto usage

:build
echo Building Docker image...
docker build -t %IMAGE_NAME%:latest .
if errorlevel 1 (
    echo Error: Build failed
    exit /b 1
)
echo [OK] Image built successfully
goto end

:run
echo Starting container...
call :cleanup_container
call :create_data_dir

REM Check if .env file exists
if exist .env (
    docker run -d --name %CONTAINER_NAME% -p %PORT%:%PORT% -v "%cd%\data:/app/data" --env-file .env --restart unless-stopped %IMAGE_NAME%:latest
) else (
    echo Warning: .env file not found. Using default configuration.
    docker run -d --name %CONTAINER_NAME% -p %PORT%:%PORT% -v "%cd%\data:/app/data" --restart unless-stopped %IMAGE_NAME%:latest
)

if errorlevel 1 (
    echo Error: Failed to start container
    exit /b 1
)
echo [OK] Container started successfully
call :show_status
goto end

:deploy
echo Full deployment starting...
echo.
call :build
if errorlevel 1 exit /b 1
echo.
call :run
goto end

:logs
echo Showing container logs (Ctrl+C to exit)...
timeout /t 2 /nobreak >nul
docker logs -f %CONTAINER_NAME%
goto end

:stop
echo Stopping container...
docker stop %CONTAINER_NAME%
if errorlevel 1 (
    echo Error: Failed to stop container
    exit /b 1
)
echo [OK] Container stopped
goto end

:start
echo Starting container...
docker start %CONTAINER_NAME%
if errorlevel 1 (
    echo Error: Failed to start container
    exit /b 1
)
echo [OK] Container started
echo Access at: http://localhost:%PORT%
goto end

:restart
echo Restarting container...
docker restart %CONTAINER_NAME%
if errorlevel 1 (
    echo Error: Failed to restart container
    exit /b 1
)
echo [OK] Container restarted
goto end

:clean
echo Cleaning up...
docker stop %CONTAINER_NAME% 2>nul
docker rm %CONTAINER_NAME% 2>nul
docker rmi %IMAGE_NAME%:latest 2>nul
echo [OK] Cleanup complete
goto end

:status
echo.
echo Container Status:
docker ps -a --filter "name=%CONTAINER_NAME%" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.
goto end

:cleanup_container
docker ps -a --format "{{.Names}}" | findstr /x %CONTAINER_NAME% >nul 2>&1
if not errorlevel 1 (
    echo Stopping and removing existing container...
    docker stop %CONTAINER_NAME% 2>nul
    docker rm %CONTAINER_NAME% 2>nul
    echo [OK] Cleanup complete
)
goto :eof

:create_data_dir
if not exist "data" (
    echo Creating data directory...
    mkdir data
    echo [OK] Data directory created
)
goto :eof

:show_status
echo.
echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo Container Name: %CONTAINER_NAME%
echo Image: %IMAGE_NAME%:latest
echo Port: %PORT%
echo.
echo Access your application at:
echo   http://localhost:%PORT%
echo.
echo Useful commands:
echo   View logs:    deploy.bat logs
echo   Stop:         deploy.bat stop
echo   Start:        deploy.bat start
echo   Restart:      deploy.bat restart
echo   Remove:       deploy.bat clean
echo.
goto :eof

:usage
echo Usage: deploy.bat {build^|run^|deploy^|logs^|stop^|start^|restart^|clean^|status}
echo.
echo Commands:
echo   build   - Build Docker image only
echo   run     - Run container (assumes image exists)
echo   deploy  - Build image and run container (full deployment)
echo   logs    - Show container logs
echo   stop    - Stop running container
echo   start   - Start stopped container
echo   restart - Restart container
echo   clean   - Remove container and image
echo   status  - Show container status
echo.
echo Examples:
echo   deploy.bat deploy    # Full deployment
echo   deploy.bat logs      # View logs
echo   deploy.bat restart   # Restart app
goto end

:end
endlocal
