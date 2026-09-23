@echo off
setlocal enabledelayedexpansion
title HuiGit - Automated Git Sync (Sukanta Hui)
color 0A

echo =====================================================================
echo          HuiGit - Automated Git Pull, Add, Commit ^& Push
echo          Developed for Sukanta Hui (Coder ^& AccoTax)
echo =====================================================================
echo.

REM 1. Check if Git is installed and accessible
where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed or not available in PATH!
    echo Please install Git from https://git-scm.com/
    pause
    exit /b 1
)

REM 2. Check if current directory is inside a Git repository
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Current directory is not a Git repository!
    pause
    exit /b 1
)

REM 3. Detect current branch
set "CURRENT_BRANCH=main"
for /f "tokens=*" %%B in ('git branch --show-current 2^>nul') do set "CURRENT_BRANCH=%%B"
if "%CURRENT_BRANCH%"=="" set "CURRENT_BRANCH=main"
echo [INFO] Working on branch: %CURRENT_BRANCH%

REM 4. Pull latest changes from remote repository
echo.
echo [1/4] Pulling latest changes from origin/%CURRENT_BRANCH%...
git pull --autostash origin %CURRENT_BRANCH%
if errorlevel 1 (
    echo [WARNING] Git pull encountered a notice or conflict. Proceeding with sync...
) else (
    echo [OK] Repository is up to date with remote.
)

REM 5. Stage all changes
echo.
echo [2/4] Staging changes (git add -A)...
git add -A
echo [OK] All modified and untracked files staged.

REM 6. Check for staged changes and commit
echo.
echo [3/4] Checking for changes to commit...
git diff --cached --quiet
if errorlevel 1 goto :do_commit

echo [INFO] No changes detected. Working tree is clean.
goto :check_push

:do_commit
set "COMMIT_MSG=%*"
if defined COMMIT_MSG (
    set "COMMIT_MSG=!COMMIT_MSG:"=!"
)

if "!COMMIT_MSG!"=="" (
    echo.
    set /p "USER_INPUT=Enter commit message (Press Enter for default timestamp message): "
    if not "!USER_INPUT!"=="" (
        set "COMMIT_MSG=!USER_INPUT!"
        set "COMMIT_MSG=!COMMIT_MSG:"=!"
    )
)

if "!COMMIT_MSG!"=="" (
    set "COMMIT_MSG=Update: %DATE% %TIME%"
)

echo [INFO] Committing with message: "!COMMIT_MSG!"
git commit -m "!COMMIT_MSG!"
if errorlevel 1 (
    echo [ERROR] Git commit failed!
    pause
    exit /b 1
)
echo [OK] Changes committed successfully.

:check_push
echo.
echo [4/4] Pushing changes to origin/%CURRENT_BRANCH%...
git push origin %CURRENT_BRANCH%
if errorlevel 1 (
    echo.
    echo =====================================================================
    echo [ERROR] Git push failed!
    echo Please verify your internet connection, credentials, or remote branch.
    echo =====================================================================
    pause
    exit /b 1
)

echo.
echo =====================================================================
echo  HuiGit SYNC COMPLETED SUCCESSFULLY!
echo =====================================================================
for /f "tokens=*" %%H in ('git rev-parse --short HEAD 2^>nul') do (
    echo  Branch: %CURRENT_BRANCH%
    echo  Latest Commit Hash: %%H
)
echo =====================================================================
echo.

REM Pause only if launched without arguments and via double-click in Explorer
if "%~1"=="" (
    echo %CMDCMDLINE% | find /i "%~0" >nul
    if not errorlevel 1 (
        pause
    )
)
exit /b 0
