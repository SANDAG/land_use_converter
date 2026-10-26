"""Script to convert existing population and household files to a pipeline hdf5 file
   to be used for the repop feature of PopulationSim"""


import pandas as pd
import os
import numpy as np
import sys
import geopandas as gpd
import ast
import warnings

_join = os.path.join

warnings.filterwarnings("ignore")


class RepopFeature(object):
    def __init__(self, params):
        self.popsim_dir = os.getcwd()
        self.parameters = pd.DataFrame()
        self.households = pd.DataFrame()
        self.xwalk = pd.DataFrame()
        self.persons = pd.DataFrame()
        self.mdldir = ""
        self.ludir = ""
        self.wdir = ""
        self.properties = {}
        self.mgra_lists = []
        self.params = params
        self.maz_file = None
        self.override = ""
        self.override_file = ""

    def __call__(self):
        self.read_inputs()
        self.create_controls()

    def read_inputs(self):
        self.parameters = pd.read_csv(self.params, usecols=["Key", "Value"])
        self.mdldir = (
            self.parameters[self.parameters.Key == "MODEL_DIR"]["Value"]
            .item()
            .strip(" ")
        )
        self.ludir = (
            self.parameters[self.parameters.Key == "LU_DIR"]["Value"].item().strip(" ")
        )
        self.wdir = (
            self.parameters[self.parameters.Key == "XWALK_DIR"]["Value"]
            .item()
            .strip(" ")
        )
        self.hhthresh = (
            self.parameters[self.parameters.Key == "HHTHRESH"]["Value"]
            .item()
            .strip(" ")
        )
        self.tazthresh = (
            self.parameters[self.parameters.Key == "TAZTHRESH"]["Value"]
            .item()
            .strip(" ")
        )
        self.override = (
            self.parameters[self.parameters.Key == "OVERRIDE"]["Value"]
            .item()
            .strip(" ")
        )
        self.override_file = (
            self.parameters[self.parameters.Key == "OVERRIDE_FILE"]["Value"]
            .item()
            .strip(" ")
        )
        self.mgra_lists = ast.literal_eval(
            self.parameters[self.parameters.Key == "SAMPLE_MGRA"]["Value"]
            .item()
            .strip(" ")
        )
        self.land_use_file = (
            self.parameters[self.parameters.Key == "LAND_USE_FILE"]["Value"]
            .item()
            .strip(" ")
        )
        self.household_file = (
            self.parameters[self.parameters.Key == "HOUSEHOLD_FILE"]["Value"]
            .item()
            .strip(" ")
        )
        self.person_file = (
            self.parameters[self.parameters.Key == "PERSON_FILE"]["Value"]
            .item()
            .strip(" ")
        )
        if self.override == "YES":
            self.override = True
            print("Override Land Use Data")
        else:
            self.override = False
            print("Append Land Use Data")
        self.xwalk = pd.read_csv(
            _join(self.popsim_dir, "setup", "data", "geo_crosswalks.csv")
        )
        self.persons = pd.read_csv(_join(self.mdldir, self.person_file)).rename(
            columns={"hhid": "hh_id"}
        )
        self.households = pd.read_csv(_join(self.mdldir, self.household_file)).rename(
            columns={"hhid": "hh_id"}
        )

    def create_controls(self, mgra_list=None):
        """create controls based on user inputs"""

        project = pd.read_excel(self.override_file, sheet_name="Project_Data").dropna(
            subset=["MGRA"]
        )
        mgra_lu = pd.read_csv(_join(self.mdldir, self.land_use_file))
        lu_filename = os.path.basename(self.land_use_file)
        if self.override:
            output_lu = pd.read_csv(_join(self.ludir, "outputs", lu_filename))
        else:
            output_lu = pd.read_csv(
                _join(self.ludir, "outputs", "temp", "mgra_changes.csv")
            )
        sf = project[project.lu_code == 101].MGRA.unique()
        mf = project[project.lu_code == 102].MGRA.unique()
        af = project[
            (project["Share Affordable"] > 0) & (project.lu_code == 102)
        ].MGRA.unique()
        mh = project[project.lu_code == 103].MGRA.unique()
        gq = project[
            (project.lu_code.isin([1402, 1403])) & (project.Beds > 0)
        ].MGRA.unique()
        daysim_dict = {1: "hh_mh", 2: "hh_sf", 3: "hh_sf", 8: "hh_mf", 9: "hh_mf"}
        households = self.households.copy()
        persons = self.persons.copy()
        households["hhtype"] = households.bldgsz.map(daysim_dict)
        households.loc[households.unittype == 1, "hhtype"] = "hh_gq"

        def get_buffer_se(mgra_list, hhtype="hh_sf"):
            """Get samples households from similar nearby mgra. Search with a half mile radius for mgras
            with matching threshold of hhtype (85%). If number of households and number of TAZs in sampel
            do not meet thresholds, expand search radius by 1/4 mile. Repeat until thresholds are met

            mgra_list: List of MGRAs with hhtype needed to sample
            hhtype: household type to sample

            note for group quarters and mobile homes, sample is taken regionally"""
            bufferhh = pd.DataFrame()
            bufferpp = pd.DataFrame()
            if hhtype in ["hh_mh", "hh_gq"]:
                buf_hh = households[households.hhtype == hhtype]
                buf_pp = persons[persons.hh_id.isin(buf_hh.hh_id.unique())]
                for mgra in mgra_list:
                    buf_hh["mgra"] = mgra
                    bufferhh = bufferhh.append(buf_hh, ignore_index=True)
                    buf_pp["mgra"] = mgra
                    bufferpp = bufferpp.append(buf_pp, ignore_index=True)
            else:
                hh_thresh = int(self.hhthresh)
                taz_thresh = int(self.tazthresh)

                for i, mgra in enumerate(mgra_list):
                    mgra_lu["threshold"] = mgra_lu[hhtype] / mgra_lu["hh"]
                    mgra_sample = mgra_lu[mgra_lu.threshold >= 0.85]
                    mgra_sample = mgra_sample.merge(
                        self.maz_file, how="left", left_on="mgra", right_on="MGRA"
                    )
                    buffer = self.maz_file[self.maz_file.MGRA == mgra]
                    buffer["geometry"] = buffer["geometry"].buffer(5280 / 2)
                    samples = gpd.sjoin(
                        gpd.GeoDataFrame(
                            mgra_sample.drop("geometry", axis=1),
                            geometry=mgra_sample.geometry,
                            crs=self.maz_file.crs,
                        ),
                        buffer,
                        how="right",
                        op="within",
                    )
                    # at least 85% of the hhtyp in question but when starting to create the distribution pic only records of that unit type
                    num_hh_sample = samples[hhtype].sum()
                    tazs = len(samples.taz.unique())
                    print(
                        "MGRA: {}, initial sample size {} {}".format(
                            mgra, num_hh_sample, tazs
                        )
                    )
                    while num_hh_sample < hh_thresh or tazs < taz_thresh:
                        print(
                            "MGRA: {}, Not enough samples. HH: {}, TAZ: {}".format(
                                mgra, num_hh_sample, tazs
                            )
                        )
                        buffer["geometry"] = buffer["geometry"].buffer(5280 / 4)
                        samples = gpd.sjoin(
                            gpd.GeoDataFrame(
                                mgra_sample.drop("geometry", axis=1),
                                geometry=mgra_sample.geometry,
                                crs=self.maz_file.crs,
                            ),
                            buffer,
                            how="right",
                            op="within",
                        )
                        # at least 85% of the hhtyp in question but when starting to create the distribution pic only records of that unit type
                        num_hh_sample = samples[hhtype].sum()
                        tazs = len(samples.taz.unique())
                        print(
                            "MGRA: {}, Final Sample Size HH: {}, TAZ:{}".format(
                                mgra, num_hh_sample, tazs
                            )
                        )
                    buf_hh = households[
                        (households.hhtype == hhtype)
                        & (households.mgra.isin(samples.mgra.unique()))
                    ]
                    buf_hh["mgra"] = mgra
                    buf_pp = persons[persons.hh_id.isin(buf_hh.hh_id.unique())]
                    buf_pp["mgra"] = mgra
                    bufferpp = bufferpp.append(buf_pp, ignore_index=True)
                    bufferhh = bufferhh.append(buf_hh, ignore_index=True)
            return bufferhh, bufferpp

        def get_buffer_from_list(mgra_list, hhtype="hh_sf"):
            """Get samples households from specific MGRA
            mgra_list: List of MGRAs to sample from
            hhtype: household type to sample from"""
            print("getting buffer se from list", hhtype, mgra_list)
            if hhtype == "hh_sf":
                prj = sf
            elif hhtype == "hh_mf":
                prj = mf
            elif hhtype == "hh_mh":
                prj = mh
            elif hhtype == "hh_af":
                prj = af
                hhtype = "hh_mf"
            else:
                prj = gq
            bufferhh = pd.DataFrame()
            bufferpp = pd.DataFrame()
            buf_hh = households[
                (households.mgra.isin(mgra_list)) & (households.hhtype == hhtype)
            ]
            buf_pp = persons[persons.hh_id.isin(buf_hh.hh_id)]

            for mgra in prj:
                buf_hh["mgra"] = mgra
                bufferhh = bufferhh.append(buf_hh, ignore_index=True)
                buf_pp["mgra"] = mgra
                bufferpp = bufferpp.append(buf_pp, ignore_index=True)
            return bufferhh, bufferpp

        def format_controls(mgra_list, buffer_hh, buffer_pp, hhtype="hh_sf"):

            if hhtype in ["hh_sf", "hh_mf", "hh_mh", "hh_af"]:
                kid_df = buffer_pp
                kid_df["kid"] = 0
                kid_df.loc[kid_df["age"] < 18, "kid"] = 1
                kid_df = kid_df.groupby("hh_id", as_index=False)["kid"].sum()
                avg4p = buffer_hh[buffer_hh.persons >= 4].persons.sum() / len(
                    buffer_hh[buffer_hh.persons >= 4]
                )
                print("Average 4p HH size for {}: {}".format(hhtype, avg4p))
                buffer_hh = buffer_hh.merge(kid_df, how="left", on="hh_id")
                buffer_hh.loc[buffer_hh.persons == 1, "hh_size_1"] = 1
                buffer_hh.loc[buffer_hh.persons == 2, "hh_size_2"] = 1
                buffer_hh.loc[buffer_hh.persons == 3, "hh_size_3"] = 1
                buffer_hh.loc[buffer_hh.persons >= 4, "hh_size_4"] = 1
                buffer_hh.loc[buffer_hh.hworkers == 0, "hh_wrks_0"] = 1
                buffer_hh.loc[buffer_hh.hworkers == 1, "hh_wrks_1"] = 1
                buffer_hh.loc[buffer_hh.hworkers == 2, "hh_wrks_2"] = 1
                buffer_hh.loc[buffer_hh.hworkers >= 3, "hh_wrks_3m"] = 1
                buffer_hh.loc[(buffer_hh["hinccat1"] == 1), "hh_inc_0_30"] = 1
                buffer_hh.loc[(buffer_hh["hinccat1"] == 2), "hh_inc_30_60"] = 1
                buffer_hh.loc[(buffer_hh["hinccat1"] == 3), "hh_inc_60_100"] = 1
                buffer_hh.loc[(buffer_hh["hinccat1"] == 4), "hh_inc_100_150"] = 1
                buffer_hh.loc[(buffer_hh["hinccat1"] == 5), "hh_inc_150_plus"] = 1
                buffer_hh.loc[buffer_hh.kid >= 1, "hh_kid"] = 1
                buffer_hh.loc[buffer_hh.kid < 1, "hh_no_kid"] = 1
                buffer_hh.loc[
                    buffer_hh.bldgsz.isin(
                        [
                            2,
                            3,
                        ]
                    ),
                    "hh_unit_single",
                ] = 1
                buffer_hh.loc[
                    buffer_hh.bldgsz.isin(
                        [
                            8,
                            9,
                        ]
                    ),
                    "hh_unit_multi",
                ] = 1
                buffer_hh.loc[
                    buffer_hh.bldgsz.isin(
                        [
                            1,
                        ]
                    ),
                    "hh_unit_mobile",
                ] = 1
                buffer_hh["tot_hh"] = 1
                buffer_hh = buffer_hh.fillna(0)
                buffer_hh = buffer_hh.groupby("mgra", as_index=False).sum()
                final_control = pd.DataFrame()
                final_control["mgra"] = mgra_list
                if hhtype == "hh_mf":
                    final_control = final_control.merge(
                        project[project.lu_code == 102][
                            ["MGRA", "Dwelling Unit", "Share Affordable"]
                        ].fillna(0),
                        left_on="mgra",
                        right_on="MGRA",
                    )
                    final_control = final_control.merge(
                        output_lu[["mgra", hhtype]], how="left", on="mgra"
                    )
                    final_control[hhtype] = final_control[hhtype] * (
                        1 - final_control["Share Affordable"]
                    )
                    final_control[hhtype] = final_control[hhtype].astype(np.int64)

                elif hhtype == "hh_af":
                    print("RUNNING AFFORDABLE HOUSING")
                    final_control = final_control.merge(
                        project[project.lu_code == 102][
                            ["MGRA", "Dwelling Unit", "Share Affordable"]
                        ],
                        left_on="mgra",
                        right_on="MGRA",
                    )
                    final_control = final_control.merge(
                        output_lu[["mgra", "hh_mf"]], how="left", on="mgra"
                    )
                    final_control[hhtype] = final_control["hh_mf"] * (
                        final_control["Share Affordable"]
                    )
                    final_control[hhtype] = final_control[hhtype].astype(np.int64)
                else:
                    final_control = final_control.merge(
                        output_lu[["mgra", hhtype]], how="left", on="mgra"
                    )
                hhctl = [
                    "hh_size_1",
                    "hh_size_2",
                    "hh_size_3",
                    "hh_size_4",
                    "hh_wrks_0",
                    "hh_wrks_1",
                    "hh_wrks_2",
                    "hh_wrks_3m",
                    "hh_inc_0_30",
                    "hh_inc_30_60",
                    "hh_inc_60_100",
                    "hh_inc_100_150",
                    "hh_inc_150_plus",
                    "hh_kid",
                    "hh_no_kid",
                    "hh_unit_single",
                    "hh_unit_multi",
                    "hh_unit_mobile",
                ]
                for control in hhctl:
                    buffer_hh[control] = buffer_hh[control] / buffer_hh["tot_hh"]
                final_control = final_control.merge(
                    buffer_hh[["mgra"] + hhctl], how="left", on="mgra"
                )
                for control in hhctl:
                    final_control[control] = (
                        final_control[hhtype] * final_control[control]
                    )
                final_control["pop"] = (
                    final_control["hh_size_1"]
                    + final_control["hh_size_2"] * 2
                    + final_control["hh_size_3"] * 3
                    + final_control["hh_size_4"] * avg4p
                )
                # person controls
                buffer_pp.loc[
                    (buffer_pp.age >= 0) & (buffer_pp.age <= 5), "age_0_5"
                ] = 1
                buffer_pp.loc[
                    (buffer_pp.age >= 6) & (buffer_pp.age < 16), "age_6_15"
                ] = 1
                buffer_pp.loc[
                    (buffer_pp.age >= 16) & (buffer_pp.age <= 17), "age_16_17"
                ] = 1
                buffer_pp.loc[
                    (buffer_pp.age >= 18) & (buffer_pp.age <= 64), "age_18_64"
                ] = 1
                buffer_pp.loc[(buffer_pp.age >= 65), "age_65p"] = 1
                buffer_pp["tot_pp"] = 1
                buffer_pp = buffer_pp.groupby("mgra", as_index=False).sum()

                ppctl = ["age_0_5", "age_6_15", "age_16_17", "age_18_64", "age_65p"]
                for control in ppctl:
                    buffer_pp[control] = buffer_pp[control] / buffer_pp["tot_pp"]
                final_control = final_control.merge(
                    buffer_pp[["mgra"] + ppctl], how="left", on="mgra"
                )
                for control in ppctl:
                    final_control[control] = (
                        final_control["pop"] * final_control[control]
                    )
            else:
                buffer_pp.loc[
                    (buffer_pp.age >= 0) & (buffer_pp.age < 16), "age_0_16"
                ] = 1
                buffer_pp.loc[
                    (buffer_pp.age >= 16) & (buffer_pp.age < 18), "age_16_18"
                ] = 1
                buffer_pp.loc[
                    (buffer_pp.age >= 18) & (buffer_pp.age < 24), "age_18_24"
                ] = 1
                buffer_pp.loc[(buffer_pp.age >= 24), "age_24p"] = 1
                buffer_pp["tot_gq"] = 1
                buffer_pp = buffer_pp.groupby("mgra", as_index=False).sum()

                ppctl = ["age_0_16", "age_16_18", "age_18_24", "age_24p"]
                for control in ppctl:
                    buffer_pp[control] = buffer_pp[control] / buffer_pp["tot_gq"]
                final_control = pd.DataFrame()
                final_control["mgra"] = mgra_list

                final_control = final_control.merge(
                    project[["MGRA", "Beds"]].rename(
                        columns={"MGRA": "mgra", "Beds": hhtype}
                    ),
                    how="left",
                    on="mgra",
                ).dropna()
                final_control = final_control.merge(
                    buffer_pp[["mgra"] + ppctl], how="left", on="mgra"
                )

                for control in ppctl:
                    final_control[control] = (
                        final_control[hhtype] * final_control[control]
                    )
            return final_control

        hhtypes = ["hh_sf", "hh_mf", "hh_mh"]
        total_control = pd.DataFrame()
        hh_namedict = {
            "hh_sf": "Single Family Households",
            "hh_mf": "Multi Family Households",
            "hh_af": "Affordable Multi Family Households",
            "hh_mh": "Mobile Homes",
        }
        has_hhpop = False
        for i, hh in enumerate([sf, mf, mh]):

            print("working on {} in MGRA: ".format(hh_namedict[hhtypes[i]]), hh)
            if len(hh) > 0:
                has_hhpop = True
                if len(self.mgra_lists[i]) > 0:
                    bufferhh, bufferpp = get_buffer_from_list(
                        self.mgra_lists[i], hhtype=hhtypes[i]
                    )
                    print(
                        "Total Sample Size for {} Households: {}".format(
                            hhtypes[i][-2:], len(bufferhh)
                        )
                    )
                    # PRINT Sample size
                else:
                    if self.maz_file is None:
                        self.maz_file = gpd.read_file(
                            _join(self.ludir, "inputs", "SANDAG_MGRA_final.shp")
                        )
                        self.maz_file = self.maz_file.to_crs({"init": "epsg:2228"})
                        self.maz_file["geometry"] = self.maz_file[
                            "geometry"
                        ].representative_point()
                    bufferhh, bufferpp = get_buffer_se(hh, hhtype=hhtypes[i])

                ctl = format_controls(hh, bufferhh, bufferpp, hhtype=hhtypes[i])
                ctl = ctl.rename(columns={"mgra": "MAZ", hhtypes[i]: "HHS"})
                # ctl.to_csv(_join(self.wdir,'repop_control_totals_maz_{}.csv'.format(hhtypes[i][-2:])),index =False)
                total_control = total_control.append(ctl, ignore_index=True)
            else:
                continue

        if has_hhpop:
            total_control = total_control.groupby("MAZ").sum()
            total_control[total_control.HHS > 0].to_csv(
                _join(self.wdir, "repop_control_totals_maz.csv")
            )

        if len(af) > 0:
            print("working on {}".format("AFs"), self.mgra_lists, self.mgra_lists[-2])

            if len(self.mgra_lists[-2]) > 0:
                bufferhh, bufferpp = get_buffer_from_list(
                    self.mgra_lists[-2], hhtype="hh_af"
                )
                if len(bufferhh) == 0:
                    print(
                        "ERROR: No households to sample from, please review mgra selection for affordable housing"
                    )
                    assert len(bufferhh) > 0
                print(
                    "Total Sample Size for {} Households: {}".format(
                        "AF", len(bufferhh)
                    )
                )
                # PRINT Sample size
            else:
                print("ERROR: No MGRA specified for affordable housing sampling")
                assert len(self.mgra_lists[-2]) > 0

            ctl = format_controls(af, bufferhh, bufferpp, hhtype="hh_af")
            ctl = ctl.rename(columns={"mgra": "MAZ", "hh_af": "HHS"})
            ctl = ctl.groupby("MAZ").sum()
            ctl[ctl.HHS > 0].to_csv(_join(self.wdir, "repop_control_totals_maz_af.csv"))

        if len(gq) > 0:
            print("working on {}".format("GQs"))

            if len(self.mgra_lists[-1]) > 0:
                bufferhh, bufferpp = get_buffer_from_list(
                    self.mgra_lists[-1], hhtype="hh_gq"
                )
                print(
                    "Total Sample Size for {} Households: {}".format(
                        "gq", len(bufferhh)
                    )
                )
                # PRINT Sample size
            else:
                bufferhh, bufferpp = get_buffer_se(gq, hhtype="hh_gq")

            ctl = format_controls(gq, bufferhh, bufferpp, hhtype="hh_gq")
            ctl = ctl.rename(columns={"mgra": "MAZ", "hh_gq": "gqs"})
            ctl = ctl.groupby("MAZ", as_index=False).sum()
            ctl.to_csv(
                _join(self.wdir, "repop_control_totals_maz_{}.csv".format("gq")),
                index=False,
            )


if __name__ == "__main__":
    rf = RepopFeature(sys.argv[1])
    rf()
