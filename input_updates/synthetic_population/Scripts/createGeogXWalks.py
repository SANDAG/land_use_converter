import pandas as pd
import sys
import os
import numpy as np

parameters_file = sys.argv[1]

parameters = pd.read_csv(parameters_file, usecols=["Key", "Value"])
WORKING_DIR = parameters[parameters.Key == "WORKING_DIR"]["Value"].item().strip(" ")


taz_puma = pd.read_csv(os.path.join(WORKING_DIR, "setup", "data", "taz_puma_xwalk.csv"))
mdldir = parameters[parameters.Key == "MODEL_DIR"]["Value"].item().strip(" ")
land_use_file = parameters[parameters.Key == "LAND_USE_FILE"]["Value"].item().strip(" ")
lu_filename = os.path.basename(land_use_file)

mgra_taz = pd.read_csv(
    os.path.join(WORKING_DIR, "..", "landuse_converter", "outputs", lu_filename),
    usecols=["mgra", "taz"],
)
mgra_taz.columns = ["MAZ", "TAZ"]
mgra_taz.merge(taz_puma, how="left", on="TAZ").drop_duplicates().astype(
    np.int64
).to_csv(os.path.join(WORKING_DIR, "setup", "data", "geo_crosswalks.csv"), index=False)
