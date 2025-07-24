@ECHO OFF
ECHO %startTime%%Time%

set ANACONDA_DIR=miniforge


call %ANACONDA_DIR%\scripts\conda.exe env create -f popsim.yml

call %ANACONDA_DIR%\scripts\conda.exe create --name geo_env 
call %ANACONDA_DIR%\scripts\activate.bat geo_env
call %ANACONDA_DIR%\scripts\conda.exe install pandas -y
call %ANACONDA_DIR%\scripts\conda.exe install geopandas -y
call %ANACONDA_DIR%\scripts\conda.exe install bokeh -y
call %ANACONDA_DIR%\scripts\conda.exe install xlsxwriter -y
call %ANACONDA_DIR%\scripts\conda.exe install xlrd -y
call %ANACONDA_DIR%\scripts\conda.exe install openpyxl -y
call %ANACONDA_DIR%\scripts\conda.exe install folium -y
call %ANACONDA_DIR%\scripts\conda.exe install pytables -y
call %ANACONDA_DIR%\scripts\conda.exe install iteround -y
call conda.bat deactivate