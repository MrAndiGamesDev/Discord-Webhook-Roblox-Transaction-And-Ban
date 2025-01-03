@echo off
REM Check if required packages are installed and up to date
set packages=datetime discord discord.py requests
set all_installed=true

for %%p in (%packages%) do (
    call :check_and_install %%p
)

if "%all_installed%"=="true" (
    echo All required packages are installed and up to date.
) else (
    echo Some packages were installed or updated.
)

REM Wait for 2 seconds before checking if the Python script exists
timeout /t 2 /nobreak >nul

REM Check if Python script exists before running
set scripts=ban.py transaction.py

for %%s in (%scripts%) do (
    if exist "./%%s" (
        echo Running %%s ...
        start python3 "%%s"
    ) else (
        echo Error: %%s not found!
    )
)

REM Log the completion of the script
echo Script execution completed at %date% %time%

timeout /t 2 nobreak >nul
exit /b

:check_and_install
set package=%1
REM Check if the package name is not empty
if "%package%"=="" (
    echo No package specified.
)

pip show %package% >nul 2>&1
if errorlevel 1 (
    echo Package %package% is not installed. Installing...
    pip install %package%
    set all_installed=false
) else (
    echo Package %package% is already installed. Checking for updates...
    pip install --upgrade %package%
    if errorlevel 1 (
        echo Failed to update package %package%.
    ) else (
        echo Package %package% is up to date.
    )
)