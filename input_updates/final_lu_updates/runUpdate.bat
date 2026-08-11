SET WORKING_DIR=%~dp0
SET TOOL_STORAGE=%1

SET ANACONDA_DIR=%TOOL_STORAGE%\dependencies\miniforge
SET CONDA_ACT=%ANACONDA_DIR%\Scripts\activate.bat
REM SET CONDA_DEACT=%ANACONDA_DIR%\Scripts\deactivate.bat
REM SET PYTHON=%ANACONDA_DIR%\python.exe
CD %ANACONDA_DIR%\Scripts
CALL %CONDA_ACT% geo_env
CD %WORKING_DIR%

call python scripts\updateLandUse.py outputs\temp\parameters.csv > 4_final_lu_updates.log


