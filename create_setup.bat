@ECHO OFF
ECHO %startTime%%Time%

::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: This file creates the folder structure needed for the SANDAG ABM2+ Application Tool
:: and copies the specified model setup and tools needed to the project directory. 
::
:: Settings:
:: emme_version:
::     set this to the same emme version used for the No Build Scenario. It will be used
::     to initialize the emme project folder.
::
:: abm_release:
::     set this to the abm release directory. Emme databanks will be initialized from here,
::     and model setup will include features of this release
::
:: tool_storage:
::     points to the folder where the SANDAG ABM2+ Application Tool is stored
::
:: net_build_dir:
::     network_build folder to be copied to the project directory
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
set emme_version=4.3.7
set abm_release="T:\ABM\release\ABM\version_14_3_0"
set tool_storage="T:\ABM\release\tools\landuse_converter\tool_storage\"
set net_build_dir="T:\projects\sr14\version14_3_0\network_build"
set net_build_years=2016 2020


:: Create Folders
mkdir network_build
mkdir input_updates
mkdir input_updates\6_reports
mkdir abm_runs
mkdir analysis
mkdir deliverables

:: create net build
robocopy %net_build_dir% network_build *.*  /XD 20* /E > create_setup.log
(for %%a in (%net_build_years%) do (
    robocopy "%net_build_dir%\%%a" "network_build\%%a" *.* /E >> create_setup.log
))

:: save run parameters
SET PARAM=input_updates\parameters.csv
ECHO emme,tool_storage,abm_release > %PARAM%
ECHO %emme_version%,%tool_storage%,%abm_release%>> %PARAM%

SET tool_storage=%tool_storage:"=%

:: Import Tools
robocopy "%tool_storage%\input_updates" *.* input_updates /E >> create_setup.log
robocopy "%tool_storage%\client_requests" *.* client_requests /E >> create_setup.log
robocopy "%tool_storage%\analysis" *.* analysis /E >> create_setup.log
copy "%tool_storage%\!README.xlsx" input_updates\..  >> create_setup.log







