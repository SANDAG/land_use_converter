import pandas as pd
import numpy as np
import os, sys

# read properties from parameters file
parameters_file = sys.argv[1]

parameters = pd.read_csv(parameters_file, usecols=["Key", "Value"])
WORKING_DIR = parameters[parameters.Key == "WORKING_DIR"]["Value"].item().strip(" ")
outputDir = os.path.join(WORKING_DIR, "Setup", "output")
XWALK_DIR = parameters[parameters.Key == "XWALK_DIR"]["Value"].item().strip(" ")
mdldir = parameters[parameters.Key == "MODEL_DIR"]["Value"].item().strip(" ")
ludir = parameters[parameters.Key == "LU_DIR"]["Value"].item().strip(" ")
override_file = parameters[parameters.Key == "OVERRIDE_FILE"]["Value"].item().strip(" ")
household_file = (
    parameters[parameters.Key == "HOUSEHOLD_FILE"]["Value"].item().strip(" ")
)
person_file = parameters[parameters.Key == "PERSON_FILE"]["Value"].item().strip(" ")
persons = pd.read_csv(os.path.join(mdldir, person_file))
personcols = persons.columns
persons = persons.rename(columns={"hhid": "hh_id"})
households = pd.read_csv(os.path.join(mdldir, household_file))
householdcols = households.columns
households = households.rename(columns={"hhid": "hh_id"})


def reformat_pop(hh, pp):
    hh = hh[["household_id", "hh_id", "MAZ"]].merge(households, how="left", on="hh_id")
    pp = pp[["household_id", "perid", "MAZ"]].merge(persons, how="left", on="perid")
    hh["mgra"] = hh["MAZ"]
    pp["mgra"] = pp["MAZ"]
    return hh, pp


combined_hh = pd.DataFrame()
combined_pp = pd.DataFrame()

for poptype in ["HH", "AF", "GQ"]:

    if os.path.isfile(os.path.join(outputDir, poptype, "synthetic_households.csv")):
        hh = pd.read_csv(os.path.join(outputDir, poptype, "synthetic_households.csv"))
        pp = pd.read_csv(os.path.join(outputDir, poptype, "synthetic_persons.csv"))
        hh, pp = reformat_pop(hh, pp)
        if poptype == "AF":
            project = pd.read_excel(override_file, sheet_name="Project_Data").dropna(
                subset=["MGRA"]
            )
            af = project[
                (project["Share Affordable"] > 0) & (project.lu_code == 102)
            ].MGRA.unique()
            hh = hh[hh.MAZ.isin(af)]
            pp = pp[pp.MAZ.isin(af)]
        if len(combined_hh) == 0:
            hh["household_id_new"] = np.arange(1, len(hh) + 1)
            hh[["household_id", "household_id_new", "hh_id"]].to_csv(
                os.path.join(outputDir, "combined", "{}_hhid_dict.csv".format(poptype)),
                index=False,
            )
            pp = pp.merge(
                hh[["household_id", "household_id_new"]], how="left", on="household_id"
            )
            hh["hhid"] = hh["household_id_new"]
            pp["hhid"] = pp["household_id_new"]
            combined_hh = hh
            combined_pp = pp

        else:
            hh["household_id_new"] = np.arange(
                combined_hh.hhid.max() + 1, combined_hh.hhid.max() + len(hh) + 1
            )
            hh[["household_id", "household_id_new", "hh_id"]].to_csv(
                os.path.join(outputDir, "combined", "{}_hhid_dict.csv".format(poptype)),
                index=False,
            )
            pp = pp.merge(
                hh[["household_id", "household_id_new"]], how="left", on="household_id"
            )
            hh["hhid"] = hh["household_id_new"]
            pp["hhid"] = pp["household_id_new"]
            combined_hh = combined_hh.append(hh, ignore_index=True)
            combined_pp = combined_pp.append(pp, ignore_index=True)


assert len(combined_hh.hhid.unique()) == len(combined_hh)

combined_hh[householdcols].to_csv(
    os.path.join(outputDir, "combined", "households.csv"), index=False
)
combined_pp[personcols].to_csv(
    os.path.join(outputDir, "combined", "persons.csv"), index=False
)
