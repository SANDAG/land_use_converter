@ECHO OFF
ECHO %startTime%%Time%
SET RUN_DIR=%~dp0
SET ROOT_DIR=%~dp0\..
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: Global Settings
::   
::
:: Settings
::     SCENARIO_TAG:     
::        name for the scenario model folder to be created under 'abm_runs'.
::
::     LANDUSE_FORM:     
::        name of filled in client land use data form which is saved under 'client_requests'.
::
::     RUN_CREATE_BASELINE:     
::        If YES, will copy the no build model folder from the specified path to the SCENARIO_TAGY 
::        folder and initialize the emme databank.
::
::     RUN_CREATE_SCENARIO:     
::        If YES, will copy the no build model folder to the SCENARIO_TAGY folder and initialize 
::        the emme databank.
::
::     RUN_01_ZONE_SPLIT: 
::        If YES will run the zone split script.
::
::     RUN_02_LANDUSE_CONVERTER: 
::        If YES will run the landuse converter step.
::
::     RUN_03_SYNTHETIC_POPULATION: 
::        If YES will run the population synthesizer. 
::
::     RUN_04_FINAL_LU_UPDATE: 
::        If YES will run the script to and update the land use file with new household data
::
::     RUN_05_HH_SAMPLING: 
::        If YES will run the household sampling step.
::
::     COPY_TO_SCENARIOS: 
::        If YES will copy updated inputs to the model scenario folders.
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SET SCENARIO_TAG=SAMPLE
SET LANDUSE_FORM=client_project_data.xlsx
SET RUN_CREATE_BASELINE=YES
SET RUN_CREATE_SCENARIO=YES
SET RUN_01_ZONE_SPLIT=YES
SET RUN_02_LANDUSE_CONVERTER=YES
SET RUN_03_SYNTHETIC_POPULATION=YES
SET RUN_04_FINAL_LU_UPDATE=YES
SET RUN_05_HH_SAMPLING=YES
SET COPY_TO_SCENARIOS=YES


::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: Create Baseline Model Folder
:: NO_BUILD_MODEL_DIR:OVER
::     points to the model setup to be used as the No Build Scenario. This will also be
::     copied to each build scenario where the inputs will be updated
::
:: VISION
::     set YES if inputs should use the CMH inputs (airport 'people mover') or NO to use Baseline inputs
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SET NO_BUILD_MODEL_DIR=***insert model directory***
SET VISION=YES

::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: 01 TAZ Split 
::   This tool updates inputs in case of a taz split
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
set SPLIT_NETWORK_DIR=%ROOT_DIR%\network_build\2016rcux_4999d

::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: 02 Land Use Converter 
::   This tool updates the MGRA land use file according to the project
::
:: Settings
::     OVERRIDE_HH:     
::        Set as YES to override existing land use in project MGRA.
::        Set as NO to keep existing land use in project MGRA and append project land use.
::
::     OVERRIDE_EMP:     
::        Set as YES to override existing land use in project MGRA.
::        Set as NO to keep existing land use in project MGRA and append project land use.
::
::     OVERRIDE_LU:     
::        Set as YES to override existing land use in project MGRA.
::        Set as NO to keep existing land use in project MGRA and append project land use.
::
::     BUFFER: 
::        Buffer distance in miles for calculating household and employment densities.
::        This distance should remain consistent with the 4D tool.
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SET OVERRIDE_HH=YES
SET OVERRIDE_EMP=YES
SET OVERRIDE_LU=YES		   
SET BUFFER=0.65

::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: 03 Synthetic Population
::    If households are added to the project, this tool runs PopulationSim in repop mode to populate them
:: Settings
::     THRESH_HH:     
::        For geographic sampling of households/population used to build controls, this sets the minimum
::        number of households needed in the sample.
::
::     THRESH_TAZ:     
::        For geographic sampling of households/population used to build controls, this sets the minimum
::        number of TAZs to be represented in the sample.
::
::     MGRA_SF:
::        To override geographic sampling of single~family households/population for controls, provide a list of MGRAs
::        from which to sample single~family housing. i.e. SET SFMGRA="[2584,5486,9782]" 
::
::     MGRA_MF:
::        To override geographic sampling of multi~family households/population for controls, provide a list of MGRAs
::        from which to sample multi-family housing. 
::
::     MGRA_MH:
::        To override geographic sampling of mobile home households/population for control, provide a list of MGRAs
::        from which to sample mobile home housing. 
::
::     MGRA_GQ:
::        To override using the regional group quarter popultion for sampling of group quarter households/population
::        for controls, provide a list of MGRAs from which to sample group~quarter housing. 
::
::     MGRA_AF:
::        If the project contains any share of affordable multi-family housing (as specified in client spreadsheet 
::        'client_project_data.xlsx'), a list of MGRAs from which to sample housing is required. If no list is provided 
::        but there is a share for affordable housing, this script will exit. 
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SET THRESH_HH=50
SET THRESH_TAZ=5
SET MGRA_SF=[]
SET MGRA_MF=[]
SET MGRA_MH=[]
SET MGRA_GQ=[]
SET MGRA_AF=[]

::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: 05 Household Sampling  
::    This tool sets a sample rate for households within given distances of the project MGRAs
::
:: Settings
::     BUFFER1:
::         First buffer distance in miles from project MGRAs to apply sample rate 1 (SAMPLE1).
::
::     BUFFER2:
::         Second buffer distance in miles from project MGRAs to apply sample rate 2 (SAMPLE2).
::
::     SAMPLE1:
::         Sample rate to be applied to households within buffer distance 1 (BUFFER1) of project MGRAs.
::
::     SAMPLE2:
::         Sample rate to be applied to households within buffer distance 2 (BUFFER2) but outside
::         buffer distance 1 (BUFFER1) of project MGRAs.
::
::     SAMPLE3:
::         Sample rate to be applied to households outside of buffer distance 2 (BUFFER2) of project MGRAs.
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SET BUFFER1=2.0
SET BUFFER2=5.0
SET SAMPLE1=1.0
SET SAMPLE2=1.0
SET SAMPLE3=1.0

::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: END User Inputs
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~




::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: Read Run Parameters
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


FOR /F "tokens=1-3* delims=," %%A IN (parameters.csv) DO (
    set EMME_VERSION=%%A
	set TOOL_STORAGE=%%B
	set ABM_RELEASE=%%C
	)
set TOOL_STORAGE=%TOOL_STORAGE:"=%

::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: Create Baseline Model Folder
:: NO_BUILD_MODEL_DIR:
::     points to the model setup to be used as the No Build Scenario. This will also be
::     copied to each build scenario where the inputs will be updated
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
FOR /F "tokens=1-2* delims= " %%A IN (%NO_BUILD_MODEL_DIR%\conf\sandag_abm.properties) DO (
    if %%A==active.logsum.matrix.file.walk.mgra ( set filename=%%C)
	if %%A==scenarioYear ( set SCENARIO_YEAR=%%C)
	if %%A==PopulationSynthesizer.InputToCTRAMP.HouseholdFile ( set householdFile=%%C)
	if %%A==PopulationSynthesizer.InputToCTRAMP.PersonFile ( set personFile=%%C)
	
	) 
SET "householdFile=%householdFile:/=\%"
SET "personFile=%personFile:/=\%"
SET ANACONDA_DIR=%TOOL_STORAGE%\dependencies\miniforge
SET CONDA_ACT=%ANACONDA_DIR%\Scripts\activate.bat
SET CONDA=%ANACONDA_DIR%\Scripts\conda.exe
SET PYTHON=%ANACONDA_DIR%\envs\geo_env\python.exe
SET SCENARIO_TAGY=%SCENARIO_TAG%_%SCENARIO_YEAR%

IF %RUN_CREATE_BASELINE%==NO goto create_scenario_step
IF EXIST %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY% (
 IF %RUN_CREATE_BASELINE%==YES goto exisiting_base )
IF NOT EXIST %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY% (
 IF %RUN_CREATE_BASELINE%==YES goto overwrite )



:exisiting_base
choice /C:YN /M:"The baseline %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY% already exists, overwrite? [YN]"
IF ERRORLEVEL ==2 GOTO no_overwrite
IF ERRORLEVEL ==1 GOTO overwrite
GOTO create_scenario_step

:overwrite
echo creating no build directory
robocopy %NO_BUILD_MODEL_DIR% %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY% *.* /XD "output" "emme_project" "application" "python" "bin" /E > %RUN_DIR%\tool.log
mkdir %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\input\original\input
mkdir %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\uec\original
mkdir %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\conf\original
mkdir %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\output
mkdir %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\python
mkdir %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\application
mkdir %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\bin
copy "%NO_BUILD_MODEL_DIR%\output\%filename%" "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\output"
copy "%NO_BUILD_MODEL_DIR%\%householdFile%" "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\input\original\%householdFile%"
copy "%NO_BUILD_MODEL_DIR%\%personFile%" "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\input\original\%personFile%"
robocopy "%ABM_RELEASE%"\common\application "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\application" *.* /E >> %RUN_DIR%\tool.log
robocopy "%ABM_RELEASE%"\common\python "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\python" *.* /E >> %RUN_DIR%\tool.log
robocopy "%ABM_RELEASE%"\common\bin "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\bin" *.* /E >> %RUN_DIR%\tool.log
robocopy "%ABM_RELEASE%"\common\input\input_checker\config "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\input_checker\config" *.* /E >> %RUN_DIR%\tool.log
robocopy "%ABM_RELEASE%"\common\input\airports\ "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\input" *SAN.csv /E >> %RUN_DIR%\tool.log
IF %VISION%==YES (
    IF %SCENARIO_YEAR% GEQ 2030 (
		ECHO Using Vision inputs; includes airport mobility hub
		ECHO Using Vision inputs; includes airport mobility hub >> %RUN_DIR%\tool.log
		copy "%ABM_RELEASE%"\common\uec\AirportModeChoice.SAN2050.xls "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\uec" >> %RUN_DIR%\tool.log
		copy "%ABM_RELEASE%"\input\2050\airport_employee_park.SAN.csv "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\input" >> %RUN_DIR%\tool.log
	) ELSE (
	    ECHO Vision Scenario before 2030; does not include airport mobility hub
        ECHO Vision Scenario before 2030; does not include airport mobility hub >> %RUN_DIR%\tool.log
        copy "%ABM_RELEASE%"\common\uec\AirportModeChoice.SAN2016.xls "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\uec" >> %RUN_DIR%\tool.log
        copy "%ABM_RELEASE%"\input\2016\airport_employee_park.SAN.csv "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\input" >> %RUN_DIR%\tool.log
	)
	
) ELSE (
    ECHO Using No Build inputs; does not include airport mobility hub
    ECHO Using No Build inputs; does not include airport mobility hub >> %RUN_DIR%\tool.log
    copy "%ABM_RELEASE%"\common\uec\AirportModeChoice.SAN2016.xls "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\uec" >> %RUN_DIR%\tool.log
    copy "%ABM_RELEASE%"\input\2016\airport_employee_park.SAN.csv "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\input" >> %RUN_DIR%\tool.log
)
REM update the property file to include new properties from the release
CALL %CONDA_ACT% geo_env
call %PYTHON% %TOOL_STORAGE%\helpers\check_properties.py %ABM_RELEASE% "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%" %VISION%
if errorlevel 1 (
    echo error in %TOOL_STORAGE%\helpers\check_properties.py python file
	call conda.bat deactivate
	cd %RUN_DIR%
	EXIT /B )
call %PYTHON% %TOOL_STORAGE%\helpers\preserve_inputs.py %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%
if errorlevel 1 (
    echo error in %TOOL_STORAGE%\helpers\preserve_inputs.py python file
	call conda.bat deactivate
	cd %RUN_DIR%
	EXIT /B )
call conda.bat deactivate
@echo init emme folder
call "%TOOL_STORAGE%"\helpers\init_emme.cmd "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%" %EMME_VERSION% "%ABM_RELEASE%"
goto create_scenario_step


:no_overwrite
echo Preserving Baseline Directory
goto create_scenario_step

:create_scenario_step
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: Create Scenario Model Folder
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
IF %RUN_CREATE_SCENARIO%==NO goto taz_split_step

IF EXIST %ROOT_DIR%\abm_runs\%SCENARIO_TAGY% (
 IF %RUN_CREATE_SCENARIO%==YES goto existing_scenario )
IF NOT EXIST %ROOT_DIR%\abm_runs\%SCENARIO_TAGY% (
 IF %RUN_CREATE_SCENARIO%==YES goto overwrite_scenario )

:existing_scenario
choice /C:YN /M:"The scenario %ROOT_DIR%\abm_runs\%SCENARIO_TAGY% already exists, overwrite? [YN]"
IF ERRORLEVEL ==2 GOTO no_overwrite_scenario
IF ERRORLEVEL ==1 GOTO overwrite_scenario
GOTO taz_split_step

:overwrite_scenario
ECHO Creating Scenario
robocopy %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY% %ROOT_DIR%\abm_runs\%SCENARIO_TAGY% *.* /XD "output" "emme_project" /E >> %RUN_DIR%\tool.log
mkdir %ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\output
@echo init emme folder
call "%TOOL_STORAGE%"\helpers\init_emme.cmd "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%" %EMME_VERSION% "%ABM_RELEASE%"
goto taz_split_step

:no_overwrite_scenario
ECHO Preserving Existing Scenario
goto taz_split_step


:taz_split_step
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: 01 TAZ Split 
::   This tool updates inputs in case of a taz split
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SET ANACONDA_DIR=%TOOL_STORAGE%\dependencies\miniforge
SET CONDA_ACT=%ANACONDA_DIR%\Scripts\activate.bat
SET CONDA=%ANACONDA_DIR%\Scripts\conda.exe
SET PYTHON=%ANACONDA_DIR%\envs\geo_env\python.exe

IF %RUN_01_ZONE_SPLIT%==NO goto landuse_converter_step
IF %RUN_01_ZONE_SPLIT%==YES goto taz_split

:taz_split
ECHO %startTime%%Time% Running TAZ Split Step...
ECHO %startTime%%Time% Running TAZ Split Step... > tool.log
cd %RUN_DIR%\1_taz_split
CALL %CONDA_ACT% geo_env
call %PYTHON% scripts\taz_split_update.py %RUN_DIR%\1_taz_split %ROOT_DIR%\abm_runs\%SCENARIO_TAGY% %ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY% %SPLIT_NETWORK_DIR% > 01_taz_split.log
if errorlevel 1 (
    echo error in TAZ SPlit
	call conda.bat deactivate
	cd %RUN_DIR%
	EXIT /B )
call conda.bat deactivate
cd %RUN_DIR%
goto landuse_converter_step


:landuse_converter_step
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: 02 Land Use Converter 
::   This tool updates the MGRA land use file according to the project
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SET MODEL_DIR=%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%
IF %RUN_02_LANDUSE_CONVERTER%==NO goto synthpop_step
IF %RUN_02_LANDUSE_CONVERTER%==YES goto landuse_converter_step

:landuse_converter_step
cd %RUN_DIR%\2_landuse_converter
del /q outputs\*
del /q outputs\temp\*
ECHO %startTime%%Time% Running Land Use Converter Tool...
ECHO %startTime%%Time% Running step 2 Land Use Converter Tool... >> %RUN_DIR%\tool.log
call runLUConverter.bat %OVERRIDE_LU% %OVERRIDE_EMP% %OVERRIDE_HH% %BUFFER% %TOOL_STORAGE% %MODEL_DIR% "%ROOT_DIR%\client_requests\%LANDUSE_FORM%" >> %RUN_DIR%\tool.log
IF NOT EXIST %RUN_DIR%\2_landuse_converter\outputs\temp\no_lu.txt (
    IF NOT EXIST %RUN_DIR%\2_landuse_converter\outputs\landuse_updates.html (
    ECHO ERROR in Land Use Converter. Please Check Log File
	cd %RUN_DIR%
	EXIT /B
	)
)
cd %RUN_DIR%
goto synthpop_step

:synthpop_step
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: 03 Synthetic Population
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SET POPSIM_PARAM=%RUN_DIR%\3_synthetic_population\Data\parameters.csv
ECHO Key,Value > %POPSIM_PARAM%
ECHO HHTHRESH,%THRESH_HH% >> %POPSIM_PARAM%
ECHO TAZTHRESH,%THRESH_TAZ% >> %POPSIM_PARAM%
ECHO SAMPLE_MGRA,"[%MGRA_SF%,%MGRA_MF%,%MGRA_MH%,%MGRA_AF%,%MGRA_GQ%]" >> %POPSIM_PARAM%
ECHO OVERRIDE,%OVERRIDE_HH% >> %POPSIM_PARAM%
ECHO OVERRIDE_FILE,%ROOT_DIR%\client_requests\%LANDUSE_FORM% >> %POPSIM_PARAM%
ECHO MODEL_DIR,%MODEL_DIR% >> %POPSIM_PARAM%
SET RUN_POPSIM=NO
IF EXIST %RUN_DIR%\2_landuse_converter\outputs\temp\has_hh.txt (
	SET RUN_POPSIM=YES)
IF EXIST %RUN_DIR%\2_landuse_converter\outputs\temp\has_gq.txt (
	SET RUN_POPSIM=YES)
IF %RUN_POPSIM%==YES ( 
    ECHO %startTime%%Time% Will Run PopulationSim Repop....
    ECHO %startTime%%Time% Will Run PopulationSim Repop.... >> %RUN_DIR%\tool.log
	goto synthpop
)
IF %RUN_POPSIM%==NO (
    if %RUN_03_SYNTHETIC_POPULATION%==YES (
		ECHO %startTime%%Time% No Households or Group Quarters....
		ECHO %startTime%%Time% No Households or Group Quarters.... >> %RUN_DIR%\tool.log
	)
	goto lu_update_step
)

:synthpop
IF %RUN_03_SYNTHETIC_POPULATION%==NO goto lu_update_step
cd %RUN_DIR%\3_synthetic_population
del /q setup\output\HH\*
del /q setup\output\AF\*
del /q setup\output\GQ\*
IF EXIST setup\data\repop* (
	del /q setup\data\repop* 
)
del /q setup\output\combined\*
ECHO %startTime%%Time% Running PopulationSim Repop....
ECHO %startTime%%Time% Running PopulationSim Repop.... >> %RUN_DIR%\tool.log
call RunAll.bat %TOOL_STORAGE% %OVERRIDE_HH% >> %RUN_DIR%\tool.log
IF NOT EXIST %RUN_DIR%\3_synthetic_population\setup\output\HH\synthetic_persons.csv ( 
	echo NO HH
	echo %RUN_DIR%\3_synthetic_population\setup\output\HH\synthetic_persons.csv
	ECHO ERROR in Synthetic Population. Please Check Log Files
	cd %RUN_DIR%
	call conda.bat deactivate
	EXIT /B
	)
IF NOT EXIST %RUN_DIR%\3_synthetic_population\setup\output\GQ\synthetic_persons.csv (  
	echo NO GQ
	ECHO ERROR in Synthetic Population. Please Check Log Files
	cd %RUN_DIR%
	call conda.bat deactivate
	EXIT /B
	)
IF NOT EXIST %RUN_DIR%\3_synthetic_population\setup\output\combined\persons.csv (  
	echo NO HH
	ECHO ERROR in Synthetic Population. Please Check Log Files
	cd %RUN_DIR%
	call conda.bat deactivate
	EXIT /B
	)
goto lu_update_step

:lu_update_step
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: 04 Landuse Update Step
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
IF %RUN_04_FINAL_LU_UPDATE%==NO goto hh_sample_step
IF %RUN_04_FINAL_LU_UPDATE%==YES goto lu_update

:lu_update
cd %RUN_DIR%\4_final_lu_updates
del /q outputs\*
SET LU_PARAM=%RUN_DIR%\4_final_lu_updates\outputs\temp\parameters.csv
ECHO Key,Value > %LU_PARAM%
ECHO WORKING_DIR,%RUN_DIR%\4_final_lu_updates >> %LU_PARAM%
ECHO MODEL_DIR,%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY% >> %LU_PARAM%
ECHO OVERRIDE_FILE,%ROOT_DIR%\client_requests\%LANDUSE_FORM% >> %LU_PARAM%
ECHO OVERRIDE,%OVERRIDE_HH% >> %LU_PARAM%
ECHO %startTime%%Time% Running Final Land Use Updates...
ECHO %startTime%%Time% Running Final Land Use Updates... >> %RUN_DIR%\tool.log
call runUpdate.bat %TOOL_STORAGE% >> %RUN_DIR%\tool.log
IF NOT EXIST %RUN_DIR%\4_final_lu_updates\outputs\*.csv (
	ECHO ERROR in Final LU Updates. Please Check Log File
	cd %RUN_DIR%
	call conda.bat deactivate
	EXIT /B
	)
cd %RUN_DIR%
call conda.bat deactivate
goto hh_sample_step
	
	
	
:hh_sample_step
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: 05 Household Sampling  
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
IF %RUN_05_HH_SAMPLING%==NO goto copy_step
IF %RUN_05_HH_SAMPLING%==YES goto hh_sample

:hh_sample
cd %RUN_DIR%\5_hh_sampling
del /q outputs\build\*
del /q outputs\no_build\*
del /q outputs\temp\*
ECHO %startTime%%Time% Running Household Sampling...
ECHO %startTime%%Time% Running Household Sampling... >> %RUN_DIR%\tool.log
call runPopSample.bat %BUFFER1% %BUFFER2% %SAMPLE1% %SAMPLE2% %SAMPLE3% %MODEL_DIR% %TOOL_STORAGE% %RUN_POPSIM% "%ROOT_DIR%\client_requests\%LANDUSE_FORM%" >> %RUN_DIR%\tool.log
IF NOT EXIST %RUN_DIR%\2_landuse_converter\outputs\temp\no_lu.txt (
	IF NOT EXIST %RUN_DIR%\5_hh_sampling\outputs\sample_rate_map.html (
		ECHO ERROR in Household Sampling. Please Check Log File
		cd %RUN_DIR%
		call conda.bat deactivate
		EXIT /B
		)
)
call conda.bat deactivate
cd %RUN_DIR%
goto copy_step

::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: Copy updated files to Build Setup |
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:copy_step
IF %COPY_TO_SCENARIOS%==NO goto finale
IF %COPY_TO_SCENARIOS%==YES goto copy_inputs

:copy_inputs
copy  "%RUN_DIR%\1_taz_split\outputs\input\*.*"  "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\input" /Y
copy  "%RUN_DIR%\1_taz_split\outputs\uec\*.*"  "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\uec" /Y
copy  "%RUN_DIR%\1_taz_split\outputs\conf\*.*"  "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\conf" /Y
copy  "%RUN_DIR%\1_taz_split\outputs\input\*.*"  "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\input" /Y
copy  "%RUN_DIR%\1_taz_split\outputs\uec\*.*"  "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\uec" /Y
copy  "%RUN_DIR%\1_taz_split\outputs\conf\*.*"  "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\conf" /Y
copy  "%RUN_DIR%\4_final_lu_updates\outputs\*.csv" "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\input" /Y
copy  "%RUN_DIR%\5_hh_sampling\outputs\build\*.csv"  "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\input" /Y
copy  "%RUN_DIR%\5_hh_sampling\outputs\no_build\*.csv"  "%ROOT_DIR%\abm_runs\no_build_%SCENARIO_TAGY%\input" /Y

mkdir "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update"
mkdir "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\1_taz_split"
mkdir "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\2_landuse_converter"
mkdir "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\3_synthetic_population"
mkdir "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\4_final_lu_updates"
mkdir "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\5_hh_sampling"
mkdir "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\5_hh_sampling\outputs"
mkdir "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\5_hh_sampling\outputs\build"
mkdir "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\5_hh_sampling\outputs\no_build"
copy "%RUN_DIR%\1_taz_split\outputs\*.*" "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\1_taz_split" /Y
copy "%RUN_DIR%\1_taz_split\*.log" "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\1_taz_split" /Y
copy "%RUN_DIR%\2_landuse_converter\outputs\*.*" "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\2_landuse_converter" /Y
copy "%RUN_DIR%\2_landuse_converter\*.log" "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\2_landuse_converter" /Y
copy "%RUN_DIR%\3_synthetic_population\Setup\output\combined\*.*" "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\3_synthetic_population" /Y
copy "%RUN_DIR%\3_synthetic_population\Setup\logs\*.*" "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\3_synthetic_population" /Y
copy "%RUN_DIR%\4_final_lu_updates\outputs\*.*" "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\4_final_lu_updates" /Y
copy "%RUN_DIR%\4_final_lu_updates\*.log" "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\4_final_lu_updates" /Y
copy "%RUN_DIR%\5_hh_sampling\outputs\*.*" "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\5_hh_sampling" /Y
copy "%RUN_DIR%\5_hh_sampling\outputs\build\*.*" "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\5_hh_sampling\outputs\build" /Y
copy "%RUN_DIR%\5_hh_sampling\outputs\no_build\*.*" "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\5_hh_sampling\outputs\no_build" /Y
copy "%RUN_DIR%\5_hh_sampling\*.log" "%ROOT_DIR%\abm_runs\%SCENARIO_TAGY%\_input_update\5_hh_sampling" /Y
goto finale

:finale
ECHO %TIME% Finished. 
ECHO %TIME% Finished. >> %RUN_DIR%\tool.log
cd %RUN_DIR%