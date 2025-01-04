@echo off
REM Check if required packages are installed and up to date
set packages=datetime discord discord.py requests tk pytz timedelta python-dotenv
set all_installed=true

set OK=[OK]:
set ERROR=[ERROR]:
set NOTE=[NOTE]:
set WARN=[WARN]:
set CAT=[ACTION]:

call :install_packages

if "%all_installed%"=="true" (
    echo %OK% All required packages are installed and up to date.
) else (
    echo %ERROR% Some packages were installed or updated.
)

REM Wait for 3 seconds before checking if the Python script exists
timeout /t 3 /nobreak >nul

call :run_scripts app.py

REM Log the completion of the script
echo %OK% Script execution completed at %date% %time%

timeout /t 3 /nobreak >nul
exit /b

:install_packages
for %%p in (%packages%) do (
    call :check_and_install %%p
)
exit /b

:check_and_install
set package=%1
REM Check if the package name is not empty
if "%package%"=="" (
    echo %ERROR% No package specified.
    timeout /t 2 /nobreak >nul
    exit /b
)

pip show %package% >nul 2>&1
if errorlevel 1 (
    echo %ERROR% Package %package% is not installed. Installing...
    pip install %package%
    set all_installed=false
) else (
    echo %OK% Package %package% is already installed. Checking for updates...
    pip install --upgrade %package%
    if errorlevel 1 (
        echo %ERROR% Failed to update package %package%.
    ) else (
        echo %OK% Package %package% is up to date.
    )
)
exit /b

:run_scripts
for %%s in (%*) do (
    if exist "%%s" (
        echo %OK% Running %%s ...
        timeout /t 3 /nobreak >nul
        start python3 %%s
    ) else (
        echo %ERROR% Error: %%s not found!
        timeout /t 3 /nobreak >nul
    )
)
exit /b