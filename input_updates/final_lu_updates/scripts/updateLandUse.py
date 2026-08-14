import pandas as pd
import sys
import os
import shutil
import numpy as np

parameters_file = sys.argv[1]
parameters = pd.read_csv(parameters_file, usecols=["Key", "Value"])
WORKING_DIR = parameters[parameters.Key == "WORKING_DIR"]["Value"].item().strip(" ")
MODEL_DIR = parameters[parameters.Key == "MODEL_DIR"]["Value"].item().strip(" ")
override = parameters[parameters.Key == "OVERRIDE"]["Value"].item().strip(" ")
override_file = parameters[parameters.Key == "OVERRIDE_FILE"]["Value"].item().strip(" ")
land_use_file = parameters[parameters.Key == "LAND_USE_FILE"]["Value"].item().strip(" ")
household_file = (
    parameters[parameters.Key == "HOUSEHOLD_FILE"]["Value"].item().strip(" ")
)
person_file = parameters[parameters.Key == "PERSON_FILE"]["Value"].item().strip(" ")
lu_filename = os.path.basename(land_use_file)
hh_filename = os.path.basename(household_file)
pp_filename = os.path.basename(person_file)

lu = pd.read_csv(
    os.path.join(WORKING_DIR, "..", "landuse_converter", "outputs", lu_filename)
)
project = (
    pd.read_excel(override_file, sheet_name="Project_Data")
    .dropna(subset=["MGRA"])
    .MGRA.unique()
)

lucols = lu.columns

has_hh = False
has_gq = False
has_neg = False
if os.path.isfile(
    os.path.join(
        WORKING_DIR, "..", "landuse_converter", "outputs", "temp", "has_hh.txt"
    )
):
    has_hh = True
if os.path.isfile(
    os.path.join(
        WORKING_DIR, "..", "landuse_converter", "outputs", "temp", "has_gq.txt"
    )
):
    has_gq = True
if os.path.isfile(
    os.path.join(
        WORKING_DIR, "..", "landuse_converter", "outputs", "temp", "negative_pop.txt"
    )
):
    has_neg = True

orig_hh = pd.read_csv(os.path.join(MODEL_DIR, household_file))

if not has_hh and not has_gq and not has_neg:
    shutil.copy(
        os.path.join(WORKING_DIR, "..", "landuse_converter", "outputs", lu_filename),
        os.path.join(WORKING_DIR, "..", "final_lu_updates", "outputs", lu_filename),
    )
    sys.exit()

if has_hh or has_gq:
    hh = pd.read_csv(
        os.path.join(
            WORKING_DIR,
            "..",
            "synthetic_population",
            "setup",
            "output",
            "combined",
            "households.csv",
        )
    )
    pop = pd.read_csv(
        os.path.join(
            WORKING_DIR,
            "..",
            "synthetic_population",
            "setup",
            "output",
            "combined",
            "persons.csv",
        )
    )
else:
    hh = pd.read_csv(os.path.join(MODEL_DIR, household_file))
    pop = pd.read_csv(os.path.join(MODEL_DIR, person_file))
if has_neg:
    hhcols = hh.columns
    popcols = pop.columns
    mgra_changes = pd.read_csv(
        os.path.join(
            WORKING_DIR,
            "..",
            "landuse_converter",
            "outputs",
            "temp",
            "mgra_changes.csv",
        )
    )
    if override == "YES":
        remove_hh = mgra_changes[mgra_changes.hh == 0].mgra.unique()
        hh = hh[~hh.mgra.isin(remove_hh)]
        pop = pop[pop.hhid.isin(hh.hhid.unique())]
    else:
        remove_hh = mgra_changes[mgra_changes.hh < 0][
            ["mgra", "hh", "hh_sf", "hh_mf", "hh_mh"]
        ]
        for idx, row in remove_hh.iterrows():
            mgra = row["mgra"]
            num_hh = abs(row["hh"])

            bldgsz_dict = {"hh_sf": [2, 3], "hh_mf": [4, 5, 6, 7, 8, 9], "hh_mh": [1]}
            for key, value in bldgsz_dict.items():
                num_hh = abs(row[key])
                if num_hh == 0:
                    continue
                else:
                    removal_df = hh[(hh.mgra == mgra) & (hh.bldgsz.isin(value))]
                    if len(removal_df) < num_hh:
                        print(
                            "WARNING: MGRA {} does not have {} {} to remove. Will remove from total households".format(
                                mgra, num_hh, key
                            )
                        )
                        additional = num_hh - len(removal_df)
                        removal_df = removal_df.append(
                            hh[(hh.mgra == mgra) & (~hh.bldgsz.isin(value))].sample(
                                additional
                            )
                        )
                    removal_id = removal_df.sample(num_hh).hhid.unique()
                    if len(removal_id) != num_hh:
                        print("ERROR: Oversampled households for removal")
                    hh = hh[~hh.hhid.isin(removal_id)]
                    pop = pop[~pop.hhid.isin(removal_id)]
    hh["hhid_new"] = np.arange(1, len(hh) + 1)
    pop = pop.merge(hh[["hhid", "hhid_new"]], how="left", on="hhid")
    pop = pop.drop("hhid", axis=1).rename(columns={"hhid_new": "hhid"})[popcols]
    hh = hh.drop("hhid", axis=1).rename(columns={"hhid_new": "hhid"})[hhcols]
    hh.to_csv(
        os.path.join(WORKING_DIR, "..", "final_lu_updates", "outputs", hh_filename),
        index=False,
    )
    pop.to_csv(
        os.path.join(WORKING_DIR, "..", "final_lu_updates", "outputs", pp_filename),
        index=False,
    )
hh = hh[hh.unittype == 0]
incbins = [
    -99999,
    15000,
    30000,
    45000,
    60000,
    75000,
    100000,
    125000,
    150000,
    200000,
    hh.hinc.max() + 1,
]
hh["hincbin"] = pd.cut(hh.hinc, incbins, labels=False)

# hhp
lu = lu.merge(
    hh.groupby("mgra", as_index=False)[["persons"]]
    .sum()
    .rename(columns={"persons": "hhp"}),
    how="left",
    on="mgra",
    suffixes=["", "_update"],
)
lu.loc[lu.mgra.isin(project), "hhp"] = lu.loc[lu.mgra.isin(project)]["hhp_update"]
lu.loc[lu.mgra.isin(project), "hhp"] = lu.loc[lu.mgra.isin(project), "hhp"].fillna(0)
# pop
lu.loc[lu.mgra.isin(project), "pop"] = (
    lu.loc[lu.mgra.isin(project)]["hhp"]
    + lu.loc[lu.mgra.isin(project)]["gq_mil"]
    + lu.loc[lu.mgra.isin(project)]["gq_civ"]
)
# hhs
lu.loc[lu.mgra.isin(project), "hhs"] = (
    lu.loc[lu.mgra.isin(project), "hhp"] / lu.loc[lu.mgra.isin(project), "hh"]
)
lu.loc[(lu.mgra.isin(project)) & (lu.hh == 0), "hhs"] = 0
# incbins
hh = (
    hh.groupby(["mgra", "hincbin"], as_index=False)[["hhid"]]
    .count()
    .pivot(index="mgra", columns="hincbin", values="hhid")
)
hh = hh.fillna(0)
inccols = ["i{}".format(i) for i in range(1, 11)]

hh.columns = inccols
lu = lu.merge(hh.reset_index(), how="left", on="mgra", suffixes=["", "_update"])

lu.loc[lu.mgra.isin(project), inccols] = (
    lu.loc[lu.mgra.isin(project)][["{}_update".format(col) for col in inccols]]
    .fillna(0)
    .to_numpy()
)
hh = hh.reset_index()
lu = lu.drop(["{}_update".format(col) for col in inccols] + ["hhp_update"], axis=1)

lu.loc[lu.mgra.isin(project), inccols] = lu.loc[lu.mgra.isin(project)][inccols].astype(
    np.int64
)
lu = lu.fillna(0)
# check data types match
orig_lu = pd.read_csv(os.path.join(MODEL_DIR, land_use_file))
for x in orig_lu.columns:
    lu[x] = lu[x].astype(orig_lu[x].dtypes.name)
lu.to_csv(
    os.path.join(WORKING_DIR, "..", "final_lu_updates", "outputs", lu_filename),
    index=False,
)
