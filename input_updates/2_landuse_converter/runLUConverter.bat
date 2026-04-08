@ECHO OFF
ECHO %startTime%%Time%

:: Configure LU Converter parameters
SET OVERRIDE_LU=%1
SET OVERRIDE_EMP=%2
SET OVERRIDE_HH=%3
rem set buffer distance for household density calculation
SET BUFFER=%4

:: Set Inputs and Directories
SET TOOL_STORAGE=%5
SET WORKING_DIR=%~dp0
SET MODEL_DIR=%6
SET OVERRIDE_FILE=%7
SET INPUT_DIR=%WORKING_DIR%inputs
SET OUTPUT_DIR=%WORKING_DIR%outputs

:: Anaconda installation directory
SET ANACONDA_DIR=%TOOL_STORAGE%\dependencies\miniforge

:: ---------------------------------------------------------------------
:: Create Parameters file 
SET PARAMETERS_FILE=%OUTPUT_DIR%\temp\parameters.csv

ECHO Key,Value > %PARAMETERS_FILE%
ECHO MODEL_DIR,%MODEL_DIR% >> %PARAMETERS_FILE%
:: T:\ABM\user\jchu\niwsc_high_density_development\input_updates\\..\abm_runs\no_build_navwar_2016 
:: Would want to point to the original model scenario/network

ECHO INPUT_DIR,%INPUT_DIR% >> %PARAMETERS_FILE%
:: T:\ABM\user\jchu\niwsc_high_density_development\input_updates\2_landuse_converter\inputs 
ECHO OUTPUT_DIR,%OUTPUT_DIR% >> %PARAMETERS_FILE%
:: T:\ABM\user\jchu\niwsc_high_density_development\input_updates\2_landuse_converter\outputs 
ECHO OVERRIDE_LU,%OVERRIDE_LU% >> %PARAMETERS_FILE%
ECHO OVERRIDE_HH,%OVERRIDE_HH% >> %PARAMETERS_FILE%
ECHO OVERRIDE_EMP,%OVERRIDE_EMP% >> %PARAMETERS_FILE%
ECHO BUFFER,%BUFFER% >> %PARAMETERS_FILE%
ECHO OVERRIDE_FILE,%OVERRIDE_FILE% >> %PARAMETERS_FILE%
:: T:\ABM\user\jchu\niwsc_high_density_development\input_updates\\..\client_requests\project_data_NAVWAR.xlsx 


:: Activate anaconda environment
SET CONDA_ACT=%ANACONDA_DIR%\Scripts\activate.bat
CD %ANACONDA_DIR%\Scripts
CALL %CONDA_ACT% geo_env
CD %WORKING_DIR%

::Run LU Converter
CALL python scripts\landuse_converter_py3.py %PARAMETERS_FILE% > 02_landuse_converter.log
