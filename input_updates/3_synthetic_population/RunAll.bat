::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: This batch file runs the entire process of Population synthesis from downloading data from Census,
:: building corsswalks, building controls and running PopulationSim. 
:: User should specify the following
::      - All required inputs
::      - Local directories
:: 		- Local Anaconda installation directory
::		- Assumes SetUpPopulationSim.bat has been run and Conda environment "popsim" exists
:: Khademul Haque, khademul.haque@rsginc.com, 04/03/2019
:: Edited by Hannah Carson, hannah.carson@rsginc.com, 04/25/2019
:: Edited by Seth Scott, sscott@fresnocog.org, 03/27/2020

:: TO DO
:: 1. make sure python call is from the same anaconda directory as in the PopulationSim setup folder
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@ECHO OFF
ECHO %startTime%%Time%

:: FLAGS - YES/NO

                    
SET RUN_CROSSWALK=YES
SET RUN_PIPE=YES
SET RUN_CONTROLS=YES
SET RUN_POPSIM_HH=YES
SET RUN_POPSIM_GQ=YES

:: set sample MGRAs for Sf/Mf/Mh/Afordable Households/Group Quarters


SET TOOL_STORAGE=%1
SET OVERRIDE=%2

SET WORKING_DIR=%~dp0
SET DATA_DIR=%WORKING_DIR%Data
SET XWALK_DIR=%WORKING_DIR%Setup\Data
SET POPSIMDIR=%WORKING_DIR%Setup
SET CONFIGDIR=%WORKING_DIR%Setup\Configs
SET LU_DIR=%WORKING_DIR%\..\2_landuse_converter




:: ---------------------------------------------------------------------
:: Create Parameters file for R scripts
SET PARAMETERS_FILE=%DATA_DIR%\parameters.csv

ECHO WORKING_DIR,%WORKING_DIR% >> %PARAMETERS_FILE%
ECHO XWALK_DIR,%XWALK_DIR% >> %PARAMETERS_FILE%
ECHO POPSIMDIR,%POPSIMDIR% >> %PARAMETERS_FILE%
ECHO LU_DIR,%LU_DIR% >> %PARAMETERS_FILE%

SET ANACONDA_DIR=%TOOL_STORAGE%\dependencies\miniforge
SET CONDA_ACT=%ANACONDA_DIR%\Scripts\activate.bat
REM SET CONDA_DEACT=%ANACONDA_DIR%\Scripts\deactivate
SET PYTHON=%ANACONDA_DIR%\envs\geo_env\python.exe
CD %ANACONDA_DIR%\Scripts
CALL %CONDA_ACT% geo_env
CD %WORKING_DIR%
REM SET ANACONDA_DIR=%TOOL_STORAGE%\dependencies\miniforge\envs\geo_env

:: Create geographic crosswalk
IF %RUN_CROSSWALK%==YES (
	ECHO %startTime%%Time%: Running script to create crosswalk...
	call python %WORKING_DIR%Scripts\createGeogXWalks.py %PARAMETERS_FILE% > Setup\logs\createGeoXWalks.log 2>&1
	if errorlevel 1 (
		echo error in synthetic population geocrosswalk
		call conda.bat deactivate
		cd %WORKING_DIR%\..
		EXIT /B )
)

IF %RUN_CONTROLS%==YES (
	ECHO %startTime%%Time%: Create controls...
	call python %WORKING_DIR%scripts\createControls.py %PARAMETERS_FILE% > Setup\logs\createControls.log 2>&1
	if errorlevel 1 (
		echo error in synthetic population controls
		call conda.bat deactivate
		cd %WORKING_DIR%\..
		EXIT /B )
)




IF %RUN_PIPE%==YES (
	ECHO %startTime%%Time%: Running script to create pipeline...
	call python %WORKING_DIR%Scripts\constructPipe.py %PARAMETERS_FILE% > Setup\logs\createPipeline.log 2>&1
	if errorlevel 1 (
		echo error in synthetic population pipeline creation
		call conda.bat deactivate
		cd %WORKING_DIR%\..
		EXIT /B )
)


	
REM CD %ANACONDA_DIR%\Scripts
REM CALL %CONDA_DEACT% 
REM call %CONDA_ACT% popsim
REM CD %WORKING_DIR%
SET ANACONDA_DIR=%TOOL_STORAGE%\dependencies\miniforge
	
 	
:: Create Controls

:: Run PopulationSim for HH population
IF %RUN_POPSIM_HH%==YES (
	IF EXIST %XWALK_DIR%\repop_control_totals_maz.csv (
		IF %OVERRIDE%==YES  (
			copy /y "%CONFIGDIR%"\HH\settings_replace.yaml "%CONFIGDIR%"\HH\settings.yaml
		)
		IF %OVERRIDE%==NO  (
			copy /y "%CONFIGDIR%"\HH\settings_append.yaml "%CONFIGDIR%"\HH\settings.yaml
		)
		ECHO %startTime%%Time%: Running PopulationSim for Households...
		CALL %POPSIMDIR%\RunPopulationSimHH.bat > Setup\Logs\populationSimHH.log 2>&1
			

		
		cd..
	)
	IF EXIST %XWALK_DIR%\repop_control_totals_maz_af.csv (
		ECHO %startTime%%Time%: Running PopulationSim for Affordable Households...
		CALL %POPSIMDIR%\RunPopulationSimAF.bat > Setup\Logs\populationSimAF.log 2>&1
			

		
		cd..
	)
)

:: Run PopulationSim for GQ population
IF %RUN_POPSIM_GQ%==YES (
	IF EXIST %XWALK_DIR%\repop_control_totals_maz_gq.csv (
		IF %OVERRIDE%==YES  (
			copy /y "%CONFIGDIR%"\GQ\settings_replace.yaml "%CONFIGDIR%"\GQ\settings.yaml
		)
		IF %OVERRIDE%==NO  (
			copy /y "%CONFIGDIR%"\GQ\settings_append.yaml "%CONFIGDIR%"\GQ\settings.yaml
		)
		ECHO %startTime%%Time%: Running PopulationSim for group quarters...
		CALL %POPSIMDIR%\RunPopulationSimGQ.bat > Setup\logs\populationSimGQ.log 2>&1
		cd..
	)
)

SET ANACONDA_DIR=%TOOL_STORAGE%\dependencies\miniforge
SET CONDA_ACT=%ANACONDA_DIR%\Scripts\activate.bat
REM SET CONDA_DEACT=%ANACONDA_DIR%\Scripts\deactivate
SET PYTHON=%ANACONDA_DIR%\envs\geo_env\python.exe
CD %ANACONDA_DIR%\Scripts
CALL %CONDA_ACT% geo_env
CD %WORKING_DIR%

:: Merge HH and GQ population
IF %RUN_POPSIM_HH%==YES  (
	ECHO %startTime%%Time%: Running Merge Populations
	CALL python %WORKING_DIR%scripts\mergeHHAFGQ.py %PARAMETERS_FILE% > Setup\logs\mergePopulation.log 2>&1
)


ECHO Success!