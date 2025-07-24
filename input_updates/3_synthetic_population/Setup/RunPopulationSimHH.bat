
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: Runs PopulationSim for HH. User should specify the following
:: 		- Local Anaconda installation directory
::		- Assumes SetUpPopulationSim.bat has been run and Conda environment "popsim" exists
:: Binny Paul, binny.mathewpaul@rsginc.com, 121517
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@ECHO OFF
ECHO %startTime%%Time%
SET BATCH_DIR=%~dp0
SET %ANACONDA_DIR%=%1
ECHO %BATCH_DIR%
:: setup paths to Python application, Conda script, etc.
SET CONDA_ACT=%ANACONDA_DIR%\Scripts\activate.bat

SET PYTHON=%ANACONDA_DIR%\envs\popsim\python.exe

:: run populationsim
ECHO Running PopulationSim....
CD %ANACONDA_DIR%\envs\popsim\Scripts
CALL %CONDA_ACT% popsim
CD %BATCH_DIR%

%PYTHON% run_populationsim.py --config configs\HH --output "output\HH"

ECHO PopulationSim run complete!!
ECHO %startTime%%Time%
