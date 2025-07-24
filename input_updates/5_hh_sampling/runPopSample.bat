@ECHO OFF
ECHO %startTime%%Time%

:: Configure LU Converter parameters
SET OVERRIDE=YES
rem set buffer distance for household sample in miles
SET BUFFER1=%1
SET BUFFER2=%2
SET SAMPLE1=%3
SET SAMPLE2=%4
SET SAMPLE3=%5
SET RUN_POPSIM=%8
:: Set Inputs and Directories
SET WORKING_DIR=%~dp0
SET MODEL_DIR=%6
SET LU_DIR=%WORKING_DIR%\..\2_landuse_converter

:: Anaconda installation directory
SET TOOL_STORAGE=%7
SET OVERRIDE_FILE=%9
SET ANACONDA_DIR=%TOOL_STORAGE%\dependencies\miniforge
SET CONDA_ACT=%ANACONDA_DIR%\Scripts\activate.bat

:: ---------------------------------------------------------------------
:: Create Parameters file 
SET PARAMETERS_FILE=%WORKING_DIR%\outputs\temp\parameters.csv

ECHO Key,Value > %PARAMETERS_FILE%
ECHO WORKING_DIR,%WORKING_DIR% >> %PARAMETERS_FILE%
ECHO MODEL_DIR,%MODEL_DIR% >> %PARAMETERS_FILE%
ECHO LU_DIR,%LU_DIR% >> %PARAMETERS_FILE%
ECHO BUFFER1,%BUFFER1% >> %PARAMETERS_FILE%
ECHO BUFFER2,%BUFFER2% >> %PARAMETERS_FILE%
ECHO SAMPLE1,%SAMPLE1% >> %PARAMETERS_FILE%
ECHO SAMPLE2,%SAMPLE2% >> %PARAMETERS_FILE%
ECHO SAMPLE3,%SAMPLE3% >> %PARAMETERS_FILE%
ECHO RUN_POPSIM,%RUN_POPSIM% >> %PARAMETERS_FILE%
ECHO OVERRIDE_FILE,%OVERRIDE_FILE% >> %PARAMETERS_FILE%


:: Activate anaconda environment
CD %ANACONDA_DIR%\Scripts
CALL %CONDA_ACT% geo_env
CD %WORKING_DIR%

::Run LU Converter
CALL python scripts\popsample.py %PARAMETERS_FILE% > 05_hh_sampling.log
