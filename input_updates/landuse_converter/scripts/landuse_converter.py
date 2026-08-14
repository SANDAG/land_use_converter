# -*- coding: utf-8 -*-
"""
Created on Fri Apr 30 10:13:16 2021
Land Use Converter for SANDAG ABM2+ Enhancement plan
@author: hannah.carson
"""
#
# Generates density variables and adds in mgra socio economic variables
#
#
# Inputs:
#   client updated landuse "client_project_data_{}.xlsx"
#   MGRA shape file with appended attributes for CPA and Residential Parcels: SANDAG_MGRA_LU.shp"
#   buffer: buffer radius for employment/dwelling unit density
#   density and employment specifications: LandUseUnitTypes.xlsx
#
# File referenced:
#   input\mgra13_based_input2016.csv
#   output\walkMgraEquivMinutes.csv
#
# Ouputs
#   updated land use file (outputs\mgra13_based_input2016.csv)
#   interactive QA/QC map (outputs\update_map.html)
#
# import inro.modeller as _m
import pandas as pd
import numpy as np
import os
import sys
import folium
import geopandas as gpd
import iteround
from folium import FeatureGroup
from folium.features import DivIcon
from shutil import copyfile
import warnings
from bokeh.layouts import column
from bokeh.plotting import output_file, save
from bokeh.models import (
    ColumnDataSource,
    TableColumn,
    DataTable,
    Paragraph,
    NumberFormatter,
    Div,
)
from bokeh.models import Tabs, TabPanel


warnings.filterwarnings("ignore")

_join = os.path.join
# TODO for documentation add that model must be setup before lu_converter is used


class LUConverter(object):
    def __init__(self, params):
        self.mgra_data_file = ""
        self.outdir = ""
        self.indir = ""
        self.mdldir = ""
        self.properties = {}
        self.buffer = 0.65
        self.mgra_shape_file = ""
        self.inmgra = pd.DataFrame()
        self.outmgra = pd.DataFrame()
        self.parameters_file = params
        self.parameters = pd.DataFrame()
        self.override_lu = False
        self.override_hh = False
        self.override_emp = False
        self.to_update_taz = False
        self.inupdate = pd.DataFrame()
        self.densities = pd.DataFrame()
        self.priority = pd.DataFrame()
        self.inshare = pd.DataFrame()
        self.lu_corr = pd.DataFrame()
        self.mgra_taz = pd.DataFrame()
        self.mgra_full = gpd.GeoDataFrame()
        self.compare_emp = pd.DataFrame()
        self.compare_housing = pd.DataFrame()
        self.compare_acre = pd.DataFrame()
        self.compare_hotel = pd.DataFrame()
        self.compare_enrollment = pd.DataFrame()
        self.compare_gqs = pd.DataFrame()
        self.final_compare = pd.DataFrame()
        self.hotel_share = pd.DataFrame()
        self.parkactive_lu = []
        self.openspaceparkpreserve_lu = []
        self.beachactive_lu = []
        self.hotel_lu = []
        self.sf_lu = []
        self.mf_lu = []
        self.mh_lu = []
        self.ah_lu = []
        self.k8 = []
        self.hsch = []
        self.coll = []
        self.oth_coll = []
        self.adlt_enrl = []
        self.zeroden_lu = []
        self.gq_civ_lu = []
        self.gq_mil_lu = []
        # outputs
        self.emp_update = pd.DataFrame()
        self.housing = pd.DataFrame()
        self.gq_pop = pd.DataFrame()
        self.enrollment = pd.DataFrame()
        self.hotels = pd.DataFrame()
        self.parks = pd.DataFrame()
        self.beach = pd.DataFrame()
        self.openspace = pd.DataFrame()
        self.density_change = pd.DataFrame()

    def __call__(self):
        self.read_inputs()
        if len(self.inupdate) == 0:
            print("No Landuse Changes made")
            with open(_join(self.outdir, "temp", "no_lu.txt"), "w") as f:
                f.write("No Landuse to update")
            f.close()
            sys.exit()
        self.create_density_matrix()
        self.update_employment()
        self.update_hotels()
        self.update_acre()
        self.update_housing()
        self.update_gqs()
        self.update_enrollment()
        self.compare_land_use()
        self.update_density()
        self.save_landuse_updates()
        self.qa_qc_map()

    def get_density(self, mgra_file, buffer):
        """Replicates 4D density calculation for employment and dwelling units."""
        mgra_landuse = mgra_file
        new_cols = ["duden", "empden"]
        # get population from synthetic population instead of mgra data file

        for col in ["duden", "empden"]:
            if col in mgra_landuse.columns:
                mgra_landuse = mgra_landuse.drop(col, axis=1)

            # merge syntetic population to landuse
        # all street distance
        equiv_min = pd.read_csv(_join(self.mdldir, self.walk_dist_file))
        equiv_min["dist"] = equiv_min["DISTWALK"]

        def density_function(mgra_in):
            eqmn = equiv_min[equiv_min["OMAZ"] == mgra_in]
            mgra_circa_oth = eqmn[eqmn["dist"] < buffer]["DMAZ"].unique()
            totEmp = mgra_landuse[mgra_landuse.mgra.isin(mgra_circa_oth)][
                "emp_total"
            ].sum()
            totHH = mgra_landuse[mgra_landuse.mgra.isin(mgra_circa_oth)][
                "hh"
            ].sum()  # TODO occupancy for hh in taz/pmsa, either user input or imputed. Assume all types have same occupancy rate if user provides. maybe use CPA for occupancy rate, CPA for development and occrate for three types
            totAcres = mgra_landuse[mgra_landuse.mgra.isin(mgra_circa_oth)][
                "land_acres"
            ].sum()
            if totAcres > 0:
                empDen = totEmp / totAcres
                duDen = totHH / totAcres
            else:
                empDen = 0
                duDen = 0
            return duDen, empDen

        mgra_landuse[new_cols[0]], mgra_landuse[new_cols[1]] = zip(
            *mgra_landuse["mgra"].map(density_function)
        )

        mgra_landuse = mgra_landuse.fillna(0)
        return mgra_landuse

    def update_lu(self, override, df, out_mgra, col_list):
        """Update the landuse file. override values if self.override is True,
        otherwise add values to existing values, update using the update dataframe "df",
        the land use dataframe "out_mgra", and the relevant columns,"col_list".
        """
        out = out_mgra.copy()
        if override:
            out.loc[list(df.index), col_list] = df.loc[list(df.index), col_list]
        else:
            out[col_list] = out[col_list].add(df[col_list], fill_value=0)
        for col in col_list:
            col_type = self.inmgra[col].dtype.name
            if col_type == "int64":
                out[col] = out[col].fillna(0).round(0).astype(col_type)
            else:
                out[col] = out[col].astype(col_type)
        return out

    def add_choro_group(
        self, map, df, group, Name, col, color, density=False, acre=False
    ):
        """Add choropleth group to map"""
        maz_df = self.mgra_full.merge(
            df[df[col] != 0]
            .reset_index()
            .rename(columns={"mgra": "MGRA"})[["MGRA", col]],
            how="left",
            on="MGRA",
        )
        maz_df = maz_df.dropna()
        if density | acre:
            maz_df[col] = maz_df[col].map(lambda x: "{:,.2f}".format(x))
        else:
            maz_df[col] = maz_df[col].map(lambda x: "{:,.0f}".format(x))
        print(df.reset_index().rename(columns={"mgra": "MGRA"}).columns)
        if len(maz_df) > 0:
            mapgroup = folium.Choropleth(
                geo_data=maz_df,
                name=Name,
                data=df.reset_index().rename(columns={"mgra": "MGRA"}),
                columns=["MGRA", col],
                key_on="feature.properties.MGRA",
                fill_color=color,
                fill_opacity=0.7,
                line_opacity=0.2,
                legend_name=Name,
                highlight=True,
            )
            mapgroup.geojson.add_to(group)
            for i, row in maz_df.iterrows():
                lat = row["geometry"].centroid.y
                lon = row["geometry"].centroid.x
                text = row[col]
                folium.map.Marker(
                    [lat, lon],
                    icon=DivIcon(
                        icon_size=(150, 36),
                        icon_anchor=(0, 0),
                        html='<div style="font-size: 8pt">%s</div>' % text,
                    ),
                ).add_to(group)
            group.add_to(map)

    def add_boundary_group(self, map, df, group, color, col):
        """Add boundary layer to map"""
        mgra_bound = folium.GeoJson(
            df,
            style_function=lambda feature: {
                "fillColor": None,
                "color": color,
                "weight": 2,
                "fillOpacity": 0,
            },
        ).add_to(group)
        for i, row in df.iterrows():
            lat = row["geometry"].centroid.y
            lon = row["geometry"].centroid.x
            text = row[col]
            folium.map.Marker(
                [lat, lon],
                icon=DivIcon(
                    icon_size=(150, 36),
                    icon_anchor=(0, 0),
                    html='<div style="font-size: 8pt">%s</div>' % text,
                ),
            ).add_to(group)
        group.add_to(map)

    def read_inputs(self):
        """Read inputs for the tool"""
        self.parameters = pd.read_csv(self.parameters_file, usecols=["Key", "Value"])
        self.outdir = (
            self.parameters[self.parameters.Key == "OUTPUT_DIR"]["Value"]
            .item()
            .strip(" ")
        )
        self.indir = (
            self.parameters[self.parameters.Key == "INPUT_DIR"]["Value"]
            .item()
            .strip(" ")
        )
        self.mdldir = (
            self.parameters[self.parameters.Key == "MODEL_DIR"]["Value"]
            .item()
            .strip(" ")
        )
        self.override_lu = (
            self.parameters[self.parameters.Key == "OVERRIDE_LU"]["Value"]
            .item()
            .strip(" ")
        )
        self.override_hh = (
            self.parameters[self.parameters.Key == "OVERRIDE_HH"]["Value"]
            .item()
            .strip(" ")
        )
        self.override_emp = (
            self.parameters[self.parameters.Key == "OVERRIDE_EMP"]["Value"]
            .item()
            .strip(" ")
        )
        self.buffer = float(
            self.parameters[self.parameters.Key == "BUFFER"]["Value"].item().strip(" ")
        )
        self.override_file = (
            self.parameters[self.parameters.Key == "OVERRIDE_FILE"]["Value"]
            .item()
            .strip(" ")
        )
        self.land_use_file = (
            self.parameters[self.parameters.Key == "LAND_USE_FILE"]["Value"]
            .item()
            .strip(" ")
        )
        self.walk_dist_file = (
            self.parameters[self.parameters.Key == "WALK_DIST_FILE"]["Value"]
            .item()
            .strip(" ")
        )
        if self.override_lu == "YES":
            self.override_lu = True
        else:
            self.override_lu = False
        if self.override_hh == "YES":
            self.override_hh = True
        else:
            self.override_hh = False
        if self.override_emp == "YES":
            self.override_emp = True
        else:
            self.override_emp = False

        # define file locations
        inputdefs = _join(self.indir, "LandUseUnitTypes.xlsx")

        # might need to change these instead to not reference the parent directories
        # if os.path.isfile(_join(self.indir,'..','..','..','network_build','data', 'mgra_zone.csv')):
        #     orig_mgra_file  = _join(self.indir,'..','..','1_taz_split','outputs',self.properties['mgra.socec.file'])
        #     self.mgra_taz    = pd.read_csv(_join(self.indir,'..','..','..','network_build','data', 'mgra_zone.csv'))
        #     self.mgra_taz.columns = [col.replace(' ','') for col in self.mgra_taz.columns]
        # else:

        orig_mgra_file = _join(self.mdldir, self.land_use_file)
        self.mgra_taz = pd.read_csv(orig_mgra_file, usecols=["mgra", "taz"])

        maz_shp = _join(self.indir, "SANDAG_MGRA_final.shp")  # need to have in setup
        # Read Inputs
        self.inmgra = pd.read_csv(orig_mgra_file)
        self.inshare = pd.read_excel(inputdefs, sheet_name="Allocation")
        self.densities = pd.read_excel(inputdefs, sheet_name="Densities")
        self.priority = pd.read_excel(inputdefs, sheet_name="Unit Type Correlation")
        self.lu_corr = pd.read_excel(inputdefs, sheet_name="LU Correspondence").fillna(
            0
        )
        self.inupdate = pd.read_excel(
            self.override_file, sheet_name="Project_Data"
        ).dropna(subset=["MGRA"])
        self.hotel_share = pd.read_excel(
            self.override_file, sheet_name="HotelRoomShare"
        ).set_index("lu_code")
        self.mgra_full = gpd.read_file(maz_shp)
        self.mgra_full = self.mgra_full.to_crs({"init": "epsg:2228"})
        self.mgra_full["mgra_acre"] = self.mgra_full.geometry.area
        self.mgra_full["mgra_acre"] = self.mgra_full.mgra_acre / 43560
        self.mgra_full = self.mgra_full.to_crs({"init": "epsg:4326"})

        # lu correspondence types for updates
        self.parkactive_lu = [l for l in self.lu_corr.parkactive_lu.unique() if l > 0]
        self.openspaceparkpreserve_lu = [
            l for l in self.lu_corr.openspaceparkpreserve_lu.unique() if l > 0
        ]
        self.beachactive_lu = [l for l in self.lu_corr.beachactive_lu.unique() if l > 0]
        self.hotel_lu = [l for l in self.lu_corr.hotel_lu.unique() if l > 0]
        self.sf_lu = [l for l in self.lu_corr.sf_lu.unique() if l > 0]
        self.mf_lu = [l for l in self.lu_corr.mf_lu.unique() if l > 0]
        self.mh_lu = [l for l in self.lu_corr.mh_lu.unique() if l > 0]
        self.k8 = [l for l in self.lu_corr.k8.unique() if l > 0]
        self.hsch = [l for l in self.lu_corr.hsch.unique() if l > 0]
        self.coll = [l for l in self.lu_corr.coll.unique() if l > 0]
        self.oth_coll = [l for l in self.lu_corr.oth_coll.unique() if l > 0]
        self.adlt_enrl = [l for l in self.lu_corr.adlt_enrl.unique() if l > 0]
        self.zeroden_lu = [l for l in self.lu_corr.zeroden_lu.unique() if l > 0]
        self.gq_civ_lu = [l for l in self.lu_corr.gq_civ_lu.unique() if l > 0]
        self.gq_mil_lu = [l for l in self.lu_corr.gq_mil_lu.unique() if l > 0]

    def create_density_matrix(self):
        """calculate and apply densities based on available attributes and priority tables"""
        # update KSF to SqFt
        self.inupdate["SqFt"] = self.inupdate["Thousand Square Feet (KSF)"] * 1000
        self.inupdate = self.inupdate.merge(
            self.mgra_full[["MGRA", "mgra_acre"]], how="left", on="MGRA"
        )
        self.inupdate.loc[self.inupdate.Acre == "MGRA", "Acre"] = self.inupdate.loc[
            self.inupdate.Acre == "MGRA"
        ].mgra_acre
        check_acre = self.inupdate[self.inupdate.Acre > self.inupdate.mgra_acre]
        if len(check_acre) > 0:
            print(
                "WARNING: MGRA acre specified is larger than MGRA area for {}. Resetting area to MGRA area".format(
                    check_acre.MGRA.unique()
                )
            )
            self.inupdate.loc[
                self.inupdate.Acre > self.inupdate.mgra_acre, "Acre"
            ] = self.inupdate.loc[
                self.inupdate.Acre > self.inupdate.mgra_acre
            ].mgra_acre

        self.inupdate["Acre"] = self.inupdate["Acre"]  # *43560
        self.inupdate = self.inupdate.set_index("lu_code")
        density_cols = self.densities.columns[2:]
        density_cols_emp = ["{}_emp".format(col) for col in density_cols]

        # create 1s matrix for input updates
        inupdate_tab = self.inupdate[density_cols]
        inupdate_tab = pd.DataFrame(
            np.where(inupdate_tab.isna(), inupdate_tab, 1),
            columns=inupdate_tab.columns,
            index=inupdate_tab.index,
        )

        # create 1s matrix for self.densities
        densities_tab = self.densities.set_index("lu_code")[density_cols]
        densities_tab = pd.DataFrame(
            np.where(densities_tab.isna(), densities_tab, 1),
            columns=densities_tab.columns,
            index=densities_tab.index,
        )
        densities_tab = densities_tab.reindex(inupdate_tab.index)

        # create priorities matrix
        priorities = self.priority.rename(
            columns={"Thousand Square Feet (KSF)": "SqFt"}
        )[
            ["lu_code"] + list(density_cols)
        ]  # .mul(densities_tab)
        priorities = priorities.loc[priorities.lu_code.isin(inupdate_tab.index)]
        priorities = priorities.set_index("lu_code").reindex(inupdate_tab.index)
        priorities = priorities.replace(99, np.nan)

        # calc priorities with available input/self.densities, use highest self.priority available
        priorities = priorities.mul(inupdate_tab).mul(densities_tab)
        priorities = priorities.where(
            priorities.values == np.expand_dims(priorities.min(axis=1), axis=1)
        )
        priorities = pd.DataFrame(
            np.where(priorities.isna(), priorities, 1),
            columns=priorities.columns,
            index=priorities.index,
        )

        # get usable self.densities in self.priority categories
        use_densities = (
            self.densities.set_index("lu_code")[density_cols]
            .reindex(inupdate_tab.index)
            .mul(priorities)
        )
        # update inputs to employees using self.densities

        self.inupdate[density_cols_emp] = self.inupdate[density_cols].div(use_densities)
        self.inupdate["Employee_from_density"] = self.inupdate[density_cols_emp].max(
            axis=1
        )
        self.inupdate["Employee_Update"] = self.inupdate["Employee"]
        self.inupdate["Employee_Update"] = np.where(
            self.inupdate["Employee_Update"].isna(),
            self.inupdate["Employee_from_density"],
            self.inupdate["Employee_Update"],
        )
        # Check for zero employment
        check_zero = self.inupdate[self.inupdate["Employee_Update"] <= 0]

        if len(check_zero) > 0:
            for i, row in check_zero.reset_index().iterrows():
                if row["lu_code"] in self.zeroden_lu:
                    continue
                else:
                    print(
                        "WARNING: Zero Employment Update in MGRA {}".format(row["MGRA"])
                    )

        # pivot employment share for use later
        self.inshare = pd.pivot(
            self.inshare,
            index="lu_code",
            columns="abm_category",
            values="value_per_unit",
        ).fillna(0)
        # save employment columns for an update

    def update_employment(self):
        """Update employment categories with land use density calculations and residential calculations"""
        self.outmgra = self.inmgra.copy().set_index("mgra")
        # update employment
        empcols = self.inshare.columns
        self.inshare = self.inshare.reset_index()

        # use mgra with an employee update
        self.emp_update = (
            self.inupdate.copy()
        )  # [self.inupdate['Employee_Update'] > 0].reset_index()
        # merge to share by employment sub-category and update
        self.emp_update = self.emp_update.merge(self.inshare, how="left", on="lu_code")
        for col in empcols:
            self.emp_update[col] = (
                self.emp_update[col] * self.emp_update["Employee_Update"]
            )
        # group parcel to mgra
        self.emp_update = self.emp_update.groupby("MGRA")[empcols].sum()
        # check negative vals
        if self.override_emp:
            if (self.emp_update.values < 0).any():
                print("Error: Cannot override with negative employment")
                sys.exit()
        else:
            check_neg = self.outmgra.copy()[empcols]
            check_neg = check_neg[empcols].add(self.emp_update[empcols], fill_value=0)
            check_neg = check_neg.loc[self.emp_update.index]
            for col in empcols:
                idx = check_neg.index[check_neg[col] < 0]
                if len(idx) > 0:
                    print("WARNING: Negative employment being zeroed out")
                    for i in list(idx):

                        self.emp_update.loc[i, col] = self.emp_update.loc[
                            i, col
                        ].item() + np.abs(check_neg.loc[i, col].item())

        self.emp_update["emp_total"] = self.emp_update[empcols].sum(axis=1)
        check_update = [
            round(a - b, 5)
            for a, b in zip(
                list(self.emp_update["emp_total"]),
                list(
                    self.inupdate[self.inupdate.Employee_Update > 0]
                    .groupby("MGRA")[["Employee_Update"]]
                    .sum()
                    .Employee_Update
                ),
            )
        ]
        if sum(check_update) > 0.0001:
            for i, diff in enumerate(check_update):
                if diff > 0:
                    print(
                        "ERROR: MisMatch in Employment Update for MGRA {}".format(
                            self.emp_update.index[i]
                        )
                    )
            sys.exit()
        # update employment based on housing
        # housing/employee
        hh_only_mgra = self.mgra_full[self.mgra_full.hh_only == 1].MGRA.unique()
        # self.mgra_full['CPNAME'] = np.where(self.mgra_full.NAME == 'SAN DIEGO',self.mgra_full.CPNAME, self.mgra_full.NAME)
        emp_msa_hh = self.inmgra[
            self.inmgra.mgra.isin(hh_only_mgra)
        ]  # .merge(self.mgra_full[self.mgra_full.hh_only ==1][['MGRA','CPNAME']].rename(columns = {'MGRA':'mgra'}), how = 'left', on = 'mgra')
        # OPTIONAL FILTER
        # emp_cpa_hh   = emp_cpa_hh[emp_cpa_hh.emp_total > 0]
        emp_msa_hh = emp_msa_hh.groupby("pseudomsa", as_index=False)[
            list(empcols) + ["emp_total", "hs"]
        ].sum()
        emp_msa_hh = pd.concat([emp_msa_hh, emp_msa_hh.sum()], ignore_index=True)
        emp_msa_hh.iloc[[-1], [0]] = "REGIONAL"
        emp_msa_hh["hh_emp"] = emp_msa_hh["hs"] / emp_msa_hh["emp_total"]
        for col in empcols:
            emp_msa_hh[col] = emp_msa_hh[col] / emp_msa_hh["emp_total"]

        hh_emp_update = self.inupdate.copy()
        hh_emp_update = hh_emp_update.groupby("MGRA").sum()
        hh_emp_update = hh_emp_update.merge(
            self.inmgra[["mgra", "pseudomsa"]].rename(columns={"mgra": "MGRA"}),
            how="left",
            on="MGRA",
        )
        hh_emp_update.loc[
            ~hh_emp_update.pseudomsa.isin(emp_msa_hh.pseudomsa.unique()), "pseudomsa"
        ] = "REGIONAL"
        hh_emp_update = hh_emp_update.merge(emp_msa_hh, how="left", on="pseudomsa")
        hh_emp_update = hh_emp_update.set_index("MGRA")
        hh_emp_update["emp_total"] = (
            hh_emp_update["Dwelling Unit"] / hh_emp_update["hh_emp"]
        )

        for col in empcols:
            hh_emp_update[col] = hh_emp_update["emp_total"] * hh_emp_update[col]
        if hh_emp_update.emp_total.sum() > 0:
            print(
                "Employment from Housing: {}".format(int(hh_emp_update.emp_total.sum()))
            )
        # add hh emp to emp update
        self.emp_update[list(empcols) + ["emp_total"]] = self.emp_update[
            list(empcols) + ["emp_total"]
        ].add(
            hh_emp_update[list(empcols) + ["emp_total"]], fill_value=0
        )  # update_lu(False,self.emp_update,hh_self.emp_update,list(empcols) + ['emp_total'])
        if len(self.emp_update) > 0:
            self.emp_update[list(empcols)] = self.emp_update[list(empcols)].apply(
                iteround.saferound, places=0
            )
        self.emp_update["emp_total"] = self.emp_update[empcols].sum(axis=1)
        self.outmgra = self.update_lu(
            self.override_emp,
            self.emp_update,
            self.outmgra,
            list(empcols) + ["emp_total"],
        )

        self.compare_emp = (
            self.inmgra[self.inmgra.mgra.isin(list(self.emp_update.index))][
                ["mgra", "emp_total"]
            ]
            .set_index("mgra")
            .merge(
                self.outmgra.loc[list(self.emp_update.index)][["emp_total"]],
                how="inner",
                suffixes=["_orig", "_update"],
                left_index=True,
                right_index=True,
            )
        )
        if self.override_emp:
            for col in [
                col.replace("_orig", "")
                for col in self.compare_emp.columns
                if col.endswith("_orig")
            ]:
                self.compare_emp["{}_new".format(col)] = self.compare_emp[
                    "{}_update".format(col)
                ]
        else:
            for col in [
                col.replace("_orig", "")
                for col in self.compare_emp.columns
                if col.endswith("_orig")
            ]:
                self.compare_emp["{}_new".format(col)] = (
                    self.compare_emp["{}_update".format(col)]
                    - self.compare_emp["{}_orig".format(col)]
                )

    def update_hotels(self):
        """Update hotel categories"""
        ##update hotel rooms
        self.hotels = self.inupdate.copy()
        self.hotels = self.hotels[self.hotels["Hotel Rooms"] > 0].rename(
            columns={"Hotel Rooms": "hotelroomtotal"}
        )
        self.hotels = self.hotels.merge(
            self.hotel_share.drop("hotelroomtotal", axis=1),
            how="left",
            left_index=True,
            right_index=True,
        )
        hotel_cols = [
            "budgetroom",
            "economyroom",
            "luxuryroom",
            "midpriceroom",
            "upscaleroom",
            "hotelroomtotal",
        ]
        for col in hotel_cols[:-1]:
            self.hotels[col] = self.hotels[col] * self.hotels.hotelroomtotal
        if len(self.hotels) > 0:
            self.hotels[hotel_cols[:-1]] = self.hotels[hotel_cols[:-1]].apply(
                iteround.saferound, places=10
            )
        # print("Hotel SubType sum: {}, hotel total sum: {}".format(self.hotels[hotel_cols[:-1]].sum().sum(),self.hotels.hotelroomtotal.sum()))

        if (
            abs(
                self.hotels[hotel_cols[:-1]].sum().sum()
                - self.hotels.hotelroomtotal.sum()
            )
            > 0.0001
        ):
            print(
                "Hotel SubType sum: {}, hotel total sum: {}".format(
                    self.hotels[hotel_cols[:-1]].sum().sum(),
                    self.hotels.hotelroomtotal.sum(),
                )
            )
            print(
                "Error: Hotel Room Types does not add up to total hotel rooms. Please check inputs"
            )
            sys.exit()

        for htl_code in list(self.hotels.index):
            if htl_code not in self.hotel_lu:
                print(
                    "Error: Hotel Rooms specified in Non-Hotel Land Use, please check inputs"
                )
                sys.exit()

        self.hotels = self.hotels.groupby("MGRA")[hotel_cols].sum()
        self.outmgra = self.update_lu(
            self.override_lu, self.hotels, self.outmgra, hotel_cols
        )
        self.compare_hotel = (
            self.inmgra[self.inmgra.mgra.isin(list(self.hotels.index))][
                ["mgra"] + hotel_cols
            ]
            .set_index("mgra")
            .merge(
                self.outmgra.loc[list(self.hotels.index)][hotel_cols],
                how="inner",
                suffixes=["_orig", "_update"],
                left_index=True,
                right_index=True,
            )
        )
        if self.override_lu:
            for col in [
                col.replace("_orig", "")
                for col in self.compare_hotel.columns
                if col.endswith("_orig")
            ]:
                self.compare_hotel["{}_new".format(col)] = self.compare_hotel[
                    "{}_update".format(col)
                ]
        else:
            for col in [
                col.replace("_orig", "")
                for col in self.compare_hotel.columns
                if col.endswith("_orig")
            ]:
                self.compare_hotel["{}_new".format(col)] = (
                    self.compare_hotel["{}_update".format(col)]
                    - self.compare_hotel["{}_orig".format(col)]
                )

    def update_acre(self):
        """Update OpenSpace categories"""
        self.inupdate = self.inupdate.reset_index()
        self.inupdate["Acre"] = self.inupdate["Acre"]  # /43560

        self.parks = self.inupdate.copy()
        self.parks.loc[
            self.parks.lu_code.isin(self.parkactive_lu), "parkactive"
        ] = self.parks[self.parks.lu_code.isin(self.parkactive_lu)][
            "Acre"
        ]  # [self.inupdate.lu_code.isin(self.parkactive_lu)]
        self.parks = self.parks.fillna(0).groupby("MGRA")[["parkactive"]].sum()
        park_cols = ["parkactive"]
        self.outmgra = self.update_lu(
            self.override_lu, self.parks, self.outmgra, park_cols
        )
        compare_park = (
            self.inmgra[self.inmgra.mgra.isin(list(self.parks.index))][
                ["mgra", "parkactive"]
            ]
            .set_index("mgra")
            .merge(
                self.outmgra.loc[list(self.parks.index)][["parkactive"]],
                how="inner",
                suffixes=["_orig", "_update"],
                left_index=True,
                right_index=True,
            )
        )

        self.openspace = (
            self.inupdate.copy()
        )  # [self.inupdate.lu_code.isin(self.openspaceparkpreserve_lu)]
        self.openspace.loc[
            self.openspace.lu_code.isin(self.openspaceparkpreserve_lu),
            "openspaceparkpreserve",
        ] = self.openspace[self.openspace.lu_code.isin(self.openspaceparkpreserve_lu)][
            "Acre"
        ]  # [self.inupdate.lu_code.isin(self.parkactive_lu)]
        self.openspace = (
            self.openspace.fillna(0).groupby("MGRA")[["openspaceparkpreserve"]].sum()
        )
        ops_cols = ["openspaceparkpreserve"]

        self.outmgra = self.update_lu(
            self.override_lu, self.openspace, self.outmgra, ops_cols
        )
        compare_openspace = (
            self.inmgra[self.inmgra.mgra.isin(list(self.openspace.index))][
                ["mgra", "openspaceparkpreserve"]
            ]
            .set_index("mgra")
            .merge(
                self.outmgra.loc[list(self.openspace.index)][["openspaceparkpreserve"]],
                how="inner",
                suffixes=["_orig", "_update"],
                left_index=True,
                right_index=True,
            )
        )

        self.beach = (
            self.inupdate.copy()
        )  # [self.inupdate.lu_code.isin(beachactive_lu)]
        self.beach.loc[
            self.beach.lu_code.isin(self.beachactive_lu), "beachactive"
        ] = self.beach[self.beach.lu_code.isin(self.beachactive_lu)][
            "Acre"
        ]  # [self.inupdate.lu_code.isin(self.parkactive_lu)]
        self.beach = (
            self.beach.fillna(0).groupby("MGRA")[["beachactive"]].sum().fillna(0)
        )
        beach_cols = ["beachactive"]

        self.outmgra = self.update_lu(
            self.override_lu, self.beach, self.outmgra, beach_cols
        )
        compare_beach = (
            self.inmgra[self.inmgra.mgra.isin(list(self.beach.index))][
                ["mgra", "beachactive"]
            ]
            .set_index("mgra")
            .merge(
                self.outmgra.loc[list(self.beach.index)][["beachactive"]],
                how="inner",
                suffixes=["_orig", "_update"],
                left_index=True,
                right_index=True,
            )
        )

        self.compare_acre = (
            compare_park.merge(
                compare_beach, how="outer", left_index=True, right_index=True
            )
            .merge(compare_openspace, how="outer", left_index=True, right_index=True)
            .fillna(0)
        )
        for suf in ["orig", "update"]:
            self.compare_acre["Acre_{}".format(suf)] = (
                self.compare_acre["parkactive_{}".format(suf)]
                + self.compare_acre["beachactive_{}".format(suf)]
                + self.compare_acre["openspaceparkpreserve_{}".format(suf)]
            )
        if self.override_lu:
            for col in [
                col.replace("_orig", "")
                for col in self.compare_acre.columns
                if col.endswith("_orig")
            ]:
                self.compare_acre["{}_new".format(col)] = self.compare_acre[
                    "{}_update".format(col)
                ]
        else:
            for col in [
                col.replace("_orig", "")
                for col in self.compare_acre.columns
                if col.endswith("_orig")
            ]:
                self.compare_acre["{}_new".format(col)] = (
                    self.compare_acre["{}_update".format(col)]
                    - self.compare_acre["{}_orig".format(col)]
                )

        ##dwelling units

    def update_housing(self):
        """Update Housing using dwelling units provided and occupancy rates from input Land-Use file"""
        # get housing occ rate by cpa
        occ_cpa = (
            self.inmgra[
                [
                    "mgra",
                    "hs",
                    "hh",
                    "hs_sf",
                    "hh_sf",
                    "hs_mf",
                    "hh_mf",
                    "hs_mh",
                    "hh_mh",
                ]
            ]
            .rename(columns={"mgra": "MGRA"})
            .merge(self.mgra_full[["MGRA", "CPNAME"]], how="left", on="MGRA")
        )
        occ_cpa = occ_cpa.groupby("CPNAME", as_index=False).sum()

        hh_types = ["sf", "mf"]
        for hh_type in hh_types:
            occ_cpa["occ_{}".format(hh_type)] = (
                occ_cpa["hh_{}".format(hh_type)] / occ_cpa["hs_{}".format(hh_type)]
            )
            occ_reg = (
                occ_cpa["hh_{}".format(hh_type)].sum()
                / occ_cpa["hs_{}".format(hh_type)].sum()
            )  # regional
            occ_cpa["occ_{}".format(hh_type)] = occ_cpa[
                "occ_{}".format(hh_type)
            ].fillna(
                occ_reg
            )  # set null to regional number

        # occ_cpa         = occ_cpa.fillna(0)
        print(occ_cpa)
        self.housing = self.inupdate.copy()  # [self.inupdate['Dwelling Unit'] > 0]
        self.housing["hs_sf"] = np.where(
            self.housing.lu_code.isin(self.sf_lu), self.housing["Dwelling Unit"], 0
        )
        self.housing["hs_mf"] = np.where(
            self.housing.lu_code.isin(self.mf_lu), self.housing["Dwelling Unit"], 0
        )
        if any(self.housing["Share Affordable"] > 1):
            print(
                "ERROR: Affordable housing share greater than 100%, please format share in decimal for ( .1, .5, .75 etc)"
            )
            sys.exit()
        self.housing["hs_af"] = np.where(
            self.housing.lu_code.isin(self.mf_lu),
            self.housing["Dwelling Unit"] * self.housing["Share Affordable"],
            0,
        )
        self.housing["hs_mh"] = np.where(
            self.housing.lu_code.isin(self.mh_lu), self.housing["Dwelling Unit"], 0
        )
        self.housing["hs"] = self.housing["Dwelling Unit"]
        self.housing = self.housing.groupby("MGRA", as_index=False).sum()

        # if self.housing['hs'].sum() > 0:
        #    with open(_join(self.outdir,'temp','has_hh.txt'),'w') as f:
        #        f.write("HAS HOUSEHOLDS: {}".format(self.housing.hs.sum()))
        #    f.close()

        self.housing = self.housing.merge(
            self.mgra_full[["MGRA", "CPNAME"]], how="left", on="MGRA"
        ).merge(
            occ_cpa[["CPNAME"] + ["occ_{}".format(hh_type) for hh_type in hh_types]],
            how="left",
            on="CPNAME",
        )
        self.housing["occ_mh"] = 1
        for hh_type in hh_types + ["mh"]:
            self.housing["hh_{}".format(hh_type)] = (
                self.housing["hs_{}".format(hh_type)]
                * self.housing["occ_{}".format(hh_type)]
            )
        self.housing["hh_af"] = self.housing["hs_af"] * self.housing["occ_mf"]
        self.housing["hh"] = (
            self.housing["hh_sf"] + self.housing["hh_mf"] + self.housing["hh_mh"]
        )

        if self.housing["hh"].sum() > 0:
            with open(_join(self.outdir, "temp", "has_hh.txt"), "w") as f:
                f.write("HAS HOUSEHOLDS: {}".format(self.housing.hh.sum()))
            f.close()

        if (
            self.housing.hs.sum()
            != self.housing[
                [
                    "hs_sf",
                    "hs_mf",
                    "hs_mh",
                ]
            ]
            .sum()
            .sum()
        ):
            print(
                "ERROR: Dwelling units specified in non-residential Land Use",
                self.housing.hs.sum(),
                self.housing[
                    [
                        "hs_sf",
                        "hs_mf",
                        "hs_mh",
                    ]
                ]
                .sum()
                .sum(),
                self.housing["Dwelling Unit"],
            )
            sys.exit()

        self.housing = self.housing.set_index("MGRA")
        housing_cols = [
            "hs",
            "hs_sf",
            "hs_mf",
            "hs_mh",
            "hh",
            "hh_sf",
            "hh_mf",
            "hh_mh",
        ]
        self.outmgra = self.update_lu(
            self.override_hh, self.housing, self.outmgra, housing_cols
        )
        self.outmgra = (
            self.outmgra.reset_index()
            .merge(
                self.housing.reset_index()[["MGRA", "hh_af"]],
                how="left",
                left_on="mgra",
                right_on="MGRA",
            )
            .fillna(0)
            .set_index("mgra")
        )
        self.inmgra["hh_af"] = 0
        self.compare_housing = (
            self.inmgra[self.inmgra.mgra.isin(list(self.housing.index))][
                ["mgra", "hh", "hh_sf", "hh_mf", "hh_af", "hh_mh"]
            ]
            .set_index("mgra")
            .merge(
                self.outmgra.loc[list(self.housing.index)][
                    ["hh", "hh_sf", "hh_mf", "hh_af", "hh_mh"]
                ],
                how="inner",
                suffixes=["_orig", "_update"],
                left_index=True,
                right_index=True,
            )[
                [
                    "{}_{}".format(i, j)
                    for i, j in zip(
                        [
                            "hh",
                            "hh",
                            "hh_sf",
                            "hh_sf",
                            "hh_mf",
                            "hh_mf",
                            "hh_af",
                            "hh_af",
                            "hh_mh",
                            "hh_mh",
                        ],
                        ["orig", "update"] * 5,
                    )
                ]
            ]
        )
        if self.override_hh:
            for col in [
                col.replace("_orig", "")
                for col in self.compare_housing.columns
                if col.endswith("_orig")
            ]:
                self.compare_housing["{}_new".format(col)] = self.compare_housing[
                    "{}_update".format(col)
                ]
        else:
            for col in [
                col.replace("_orig", "")
                for col in self.compare_housing.columns
                if col.endswith("_orig")
            ]:
                self.compare_housing["{}_new".format(col)] = (
                    self.compare_housing["{}_update".format(col)]
                    - self.compare_housing["{}_orig".format(col)]
                )

    def update_gqs(self):
        """update group quarters categories"""
        # update group quarters
        self.gq_pop = self.inupdate.copy()
        self.gq_pop["gq_civ"] = np.where(
            self.gq_pop.lu_code.isin(self.gq_civ_lu), self.gq_pop["Beds"], 0
        )
        self.gq_pop["gq_mil"] = np.where(
            self.gq_pop.lu_code.isin(self.gq_mil_lu), self.gq_pop["Beds"], 0
        )
        self.gq_pop = self.gq_pop.groupby("MGRA").sum()
        gq_cols = ["gq_civ", "gq_mil"]
        if self.gq_pop[["gq_civ", "gq_mil"]].sum().sum() > 0:
            with open(_join(self.outdir, "temp", "has_gq.txt"), "w") as f:
                f.write(
                    "HAS GROUP-QUARTERS: {}".format(
                        self.gq_pop[["gq_civ", "gq_mil"]].sum().sum()
                    )
                )
            f.close()

        self.outmgra = self.update_lu(
            self.override_hh, self.gq_pop, self.outmgra, gq_cols
        )
        self.compare_gqs = (
            self.inmgra[self.inmgra.mgra.isin(list(self.gq_pop.index))][
                ["mgra"] + gq_cols
            ]
            .set_index("mgra")
            .merge(
                self.outmgra.loc[list(self.gq_pop.index)][gq_cols],
                how="inner",
                suffixes=["_orig", "_update"],
                left_index=True,
                right_index=True,
            )[
                [
                    "{}_{}".format(i, j)
                    for i, j in zip(
                        ["gq_civ", "gq_civ", "gq_mil", "gq_mil"], ["orig", "update"] * 2
                    )
                ]
            ]
        )
        self.compare_gqs["tot_gq_orig"] = (
            self.compare_gqs["gq_civ_orig"] + self.compare_gqs["gq_mil_orig"]
        )
        self.compare_gqs["tot_gq_update"] = (
            self.compare_gqs["gq_civ_update"] + self.compare_gqs["gq_mil_update"]
        )
        if self.override_hh:
            for col in [
                col.replace("_orig", "")
                for col in self.compare_gqs.columns
                if col.endswith("_orig")
            ]:
                self.compare_gqs["{}_new".format(col)] = self.compare_gqs[
                    "{}_update".format(col)
                ]
        else:
            for col in [
                col.replace("_orig", "")
                for col in self.compare_gqs.columns
                if col.endswith("_orig")
            ]:
                self.compare_gqs["{}_new".format(col)] = (
                    self.compare_gqs["{}_update".format(col)]
                    - self.compare_gqs["{}_orig".format(col)]
                )

    def update_enrollment(self):
        """update enrollment categories"""
        # enrollment
        self.enrollment = self.inupdate  # [self.inupdate['Students'] > 0]
        self.enrollment["enrollgradekto8"] = np.where(
            self.enrollment.lu_code.isin(self.k8), self.enrollment["Students"], 0
        )
        self.enrollment["enrollgrade9to12"] = np.where(
            self.enrollment.lu_code.isin(self.hsch), self.enrollment["Students"], 0
        )
        self.enrollment["collegeenroll"] = np.where(
            self.enrollment.lu_code.isin(self.coll), self.enrollment["Students"], 0
        )
        self.enrollment["othercollegeenroll"] = np.where(
            self.enrollment.lu_code.isin(self.oth_coll), self.enrollment["Students"], 0
        )
        self.enrollment["adultschenrl"] = np.where(
            self.enrollment.lu_code.isin(self.adlt_enrl), self.enrollment["Students"], 0
        )
        self.enrollment["tot_enroll"] = self.enrollment["Students"]
        self.enrollment = self.enrollment.groupby("MGRA").sum()
        enroll_cols = [
            "enrollgradekto8",
            "enrollgrade9to12",
            "collegeenroll",
            "othercollegeenroll",
            "adultschenrl",
        ]

        if (
            self.enrollment.tot_enroll.sum()
            != self.enrollment[
                [
                    "enrollgradekto8",
                    "enrollgrade9to12",
                    "collegeenroll",
                    "othercollegeenroll",
                    "adultschenrl",
                ]
            ]
            .sum()
            .sum()
        ):
            print("ERROR: Student Enrollment specified in Non-School Land Use")
            sys.exit()

        self.outmgra = self.update_lu(
            self.override_lu, self.enrollment, self.outmgra, enroll_cols
        )
        self.compare_enrollment = (
            self.inmgra[self.inmgra.mgra.isin(list(self.enrollment.index))][
                [
                    "mgra",
                    "enrollgradekto8",
                    "enrollgrade9to12",
                    "collegeenroll",
                    "othercollegeenroll",
                    "adultschenrl",
                ]
            ]
            .set_index("mgra")
            .merge(
                self.outmgra.loc[list(self.enrollment.index)][
                    [
                        "enrollgradekto8",
                        "enrollgrade9to12",
                        "collegeenroll",
                        "othercollegeenroll",
                        "adultschenrl",
                    ]
                ],
                how="inner",
                suffixes=["_orig", "_update"],
                left_index=True,
                right_index=True,
            )[
                [
                    "{}_{}".format(i, j)
                    for i, j in zip(
                        [
                            "enrollgradekto8",
                            "enrollgradekto8",
                            "enrollgrade9to12",
                            "enrollgrade9to12",
                            "collegeenroll",
                            "collegeenroll",
                            "othercollegeenroll",
                            "othercollegeenroll",
                            "adultschenrl",
                            "adultschenrl",
                        ],
                        ["orig", "update"] * 5,
                    )
                ]
            ]
        )

        for suf in ["orig", "update"]:
            self.compare_enrollment["tot_enroll_{}".format(suf)] = (
                self.compare_enrollment["enrollgradekto8_{}".format(suf)]
                + self.compare_enrollment["enrollgrade9to12_{}".format(suf)]
                + self.compare_enrollment["collegeenroll_{}".format(suf)]
                + self.compare_enrollment["othercollegeenroll_{}".format(suf)]
                + self.compare_enrollment["adultschenrl_{}".format(suf)]
            )
        if self.override_lu:
            for col in [
                col.replace("_orig", "")
                for col in self.compare_enrollment.columns
                if col.endswith("_orig")
            ]:
                self.compare_enrollment["{}_new".format(col)] = self.compare_enrollment[
                    "{}_update".format(col)
                ]
        else:
            for col in [
                col.replace("_orig", "")
                for col in self.compare_enrollment.columns
                if col.endswith("_orig")
            ]:
                self.compare_enrollment["{}_new".format(col)] = (
                    self.compare_enrollment["{}_update".format(col)]
                    - self.compare_enrollment["{}_orig".format(col)]
                )

    def compare_land_use(self):
        """Create a summary of land-use changes"""
        # summarize all changes
        # if os.path.isfile(_join(self.outdir,'MGRA_Summary.xlsx')):
        # os.remove(_join(self.outdir,'MGRA_Summary.xlsx'))
        # copyfile(_join(self.outdir,'MGRA_Summary_template.xlsx'),_join(self.outdir,'MGRA_Summary.xlsx'))
        # workbook = openpyxl.load_workbook(_join(self.outdir,'MGRA_Summary.xlsx'))
        # writer = pd.ExcelWriter(_join(self.outdir,'MGRA_Summary.xlsx'), engine='openpyxl')
        # writer.book = workbook
        # writer.sheets = dict((ws.title, ws) for ws in workbook.worksheets)

        self.final_compare = (
            self.compare_housing[
                [
                    "hh_orig",
                    "hh_update",
                    "hh_new",
                    "hh_sf_orig",
                    "hh_sf_update",
                    "hh_sf_new",
                    "hh_mf_orig",
                    "hh_mf_update",
                    "hh_mf_new",
                    "hh_af_orig",
                    "hh_af_update",
                    "hh_af_new",
                    "hh_mh_orig",
                    "hh_mh_update",
                    "hh_mh_new",
                ]
            ]
            .merge(
                self.compare_acre[["Acre_orig", "Acre_update", "Acre_new"]],
                how="outer",
                left_index=True,
                right_index=True,
            )
            .merge(self.compare_emp, how="outer", left_index=True, right_index=True)
            .merge(
                self.compare_enrollment[
                    ["tot_enroll_orig", "tot_enroll_update", "tot_enroll_new"]
                ],
                how="outer",
                left_index=True,
                right_index=True,
            )
            .merge(
                self.compare_gqs[["tot_gq_orig", "tot_gq_update", "tot_gq_new"]],
                how="outer",
                left_index=True,
                right_index=True,
            )
            .merge(self.compare_hotel, how="outer", left_index=True, right_index=True)
            .fillna(0)
        )
        # for col in [col for col in self.final_compare.columns if col.endswith('_orig')]:
        # if self.override:
        # self.final_compare[col.replace('_orig','_new')] = self.final_compare[col.replace('_orig','_update')]
        # else:
        # self.final_compare[col.replace('_orig','_new')] = self.final_compare[col.replace('_orig','_update')] - self.final_compare[col]
        # mgra_change = self.final_compare[[col for col in self.final_compare.columns if col.endswith('_new')]]
        # mgra_change.columns = [col.replace('_new','') for col in mgra_change.columns]
        # mgra_change.to_csv(_join(self.outdir,'mgra_changes.csv'))
        # mgra_change.columns = [col.replace('_new','') for col in mgra_change.columns]
        mgra_change = self.final_compare[
            [col for col in self.final_compare.columns if col.endswith("_new")]
        ]
        mgra_change.columns = [col.replace("_new", "") for col in mgra_change.columns]
        mgra_change.to_csv(_join(self.outdir, "temp", "mgra_changes.csv"))

    def update_density(self):
        """Update dwelling unit and employment density"""
        self.outmgra_density = self.get_density(self.outmgra.reset_index(), self.buffer)

    def save_landuse_updates(self):
        """save updated lu file"""
        out_mgra = self.outmgra_density[self.inmgra.columns].drop("hh_af", axis=1)
        for x in out_mgra.columns:
            if self.inmgra[x].dtypes.name == "int64":
                out_mgra[x] = out_mgra[x].round(0).astype(self.inmgra[x].dtypes.name)
            else:
                out_mgra[x] = out_mgra[x].astype(self.inmgra[x].dtypes.name)

        out_mgra.to_csv(
            _join(self.outdir, os.path.basename(self.land_use_file)), index=False
        )

    def qa_qc_map(self):
        """Create HTML QA/QC maps to show mgra boundaries of updated mgras. Layers are
        drawn only if there are changes to that layer."""
        # format final compare dataframes
        final_compare_init = self.final_compare[
            [col for col in self.final_compare.columns if col.endswith("_orig")]
        ]
        final_compare_init.loc["Total"] = final_compare_init.sum()
        final_compare_update = self.final_compare[
            [col for col in self.final_compare.columns if col.endswith("_update")]
        ]
        final_compare_update["hh_af_update"] = (
            final_compare_update["hh_af_update"] / final_compare_update["hh_mf_update"]
        )
        final_compare_update["af_units"] = (
            final_compare_update["hh_mf_update"] * final_compare_update["hh_af_update"]
        )
        final_compare_update.loc["Total"] = final_compare_update.sum()
        final_compare_update.loc["Total", "hh_af_update"] = (
            final_compare_update.loc["Total"]["af_units"]
            / final_compare_update.loc["Total"]["hh_mf_update"]
        )
        final_compare_update = final_compare_update.drop("af_units", axis=1)
        coldict = {
            "mgra": "MGRA",
            "hh": "Households",
            "hh_sf": "Single-Family Households",
            "hh_mf": "Multi-Family Households",
            "hh_af": "Affordable Multi-Family Households Share",
            "hh_mh": "Mobile Home Households",
            "Acre": "Open Space Acres",
            "emp_total": "Employment",
            "budgetroom": "Budget Hotel Room",
            "economyroom": "Economy Hotel Room",
            "luxuryroom": "Luxury Hotel Room",
            "midpriceroom": "Mid-Price Hotel Room",
            "upscaleroom": "Upscale Hotel Room",
            "hotelroomtotal": "Total Hotel Rooms",
            "tot_enroll": "Enrollment",
            "tot_gq": "Group Quarters",
        }
        # format tables for html panel
        table_height = 75 + len(final_compare_init) * 10
        source1 = ColumnDataSource(final_compare_init.reset_index())
        columns1 = [TableColumn(field="mgra", title="MGRA")] + [
            TableColumn(
                field=col,
                title=coldict[col.replace("_orig", "")],
                formatter=NumberFormatter(format="0,0", text_align="right"),
            )
            for col in final_compare_init.columns
        ]

        table1 = DataTable(
            source=source1,
            columns=columns1,
            autosize_mode="fit_viewport",
            index_position=None,
            margin=(5, 5, -5, 5),
            height=table_height,
        )

        source2 = ColumnDataSource(final_compare_update.fillna(0).reset_index())
        columns2 = [TableColumn(field="mgra", title="MGRA")] + [
            TableColumn(
                field=col,
                title=coldict[col.replace("_update", "")],
                formatter=NumberFormatter(format="0,0", text_align="right"),
            )
            if col != "hh_af_update"
            else TableColumn(
                field=col,
                title=coldict[col.replace("_update", "")],
                formatter=NumberFormatter(format="0,0.00", text_align="right"),
            )
            for col in final_compare_update.columns
        ]
        title1 = Paragraph(text="No Build Land Use Inputs")
        title2 = Paragraph(text="Build Land Use Inputs")
        table2 = DataTable(
            source=source2,
            columns=columns2,
            autosize_mode="fit_viewport",
            index_position=None,
            height=table_height,
        )

        final_compare_update.columns = final_compare_init.columns
        final_compare_delta = final_compare_update.subtract(
            final_compare_init, fill_value=0
        )

        source3 = ColumnDataSource(final_compare_delta.fillna(0).reset_index())
        columns3 = [TableColumn(field="mgra", title="MGRA")] + [
            TableColumn(
                field=col,
                title=coldict[col.replace("_orig", "")],
                formatter=NumberFormatter(format="0,0", text_align="right"),
            )
            if col != "hh_af_orig"
            else TableColumn(
                field=col,
                title=coldict[col.replace("_orig", "")],
                formatter=NumberFormatter(format="0,0.00", text_align="right"),
            )
            for col in final_compare_update.columns
        ]
        table3 = DataTable(
            source=source3,
            columns=columns3,
            autosize_mode="fit_viewport",
            index_position=None,
            height=table_height,
        )
        title3 = Paragraph(text="Change in Land Use Inputs")

        neg_cols = []
        for col in final_compare_delta.columns:
            if final_compare_delta[col].min() < 0:
                neg_cols.append(coldict[col.replace("_orig", "")])
        if len(neg_cols) > 0:
            print("NEGATIVE COLS", neg_cols)
            if "Households" in neg_cols or "Group Quarters" in neg_cols:
                with open(_join(self.outdir, "temp", "negative_pop.txt"), "w") as f:
                    f.write("Pop has been removed")
            title4 = Paragraph(
                text="No Build Land Use Overriden in {}".format(neg_cols)
            )
            layout1 = column(title1, table1, title2, table2, title3, table3, title4)
        else:
            layout1 = column(title1, table1, title2, table2, title3, table3)
        tab1 = TabPanel(child=layout1, title="Land Use Data")

        # create map
        self.mgra_full["mgra_label"] = self.mgra_full[
            "MGRA"
        ]  # .map(lambda b: 'MGRA {}'.format(b))

        self.mgra_full["x"] = self.mgra_full.geometry.centroid.x
        self.mgra_full["y"] = self.mgra_full.geometry.centroid.y

        # create tables for map display
        inmgra_density = self.inmgra.copy()  # get_density(inmgra)
        self.density_change = inmgra_density[["mgra", "duden", "empden"]].merge(
            self.outmgra_density[["mgra", "duden", "empden"]],
            how="inner",
            on="mgra",
            suffixes=["_in", "_out"],
        )
        self.density_change["changed_duden"] = False
        self.density_change.loc[
            abs(self.density_change["duden_in"] - self.density_change["duden_out"])
            > 0.00011,
            "changed_duden",
        ] = True
        self.density_change["changed_empden"] = False
        self.density_change.loc[
            abs(self.density_change["empden_in"] - self.density_change["empden_out"])
            > 0.00011,
            "changed_empden",
        ] = True

        if self.to_update_taz:
            orig_taz = self.mgra_full.merge(
                self.inmgra[["mgra", "taz"]],
                how="left",
                left_on="MGRA",
                right_on="mgra",
            ).dissolve(by="taz", as_index=False)
            orig_taz["taz_label"] = orig_taz["taz"].map(
                lambda n: "Original TAZ {}".format(int(n))
            )
            update_taz = self.mgra_full.merge(
                self.outmgra.reset_index()[["mgra", "taz"]],
                how="left",
                left_on="MGRA",
                right_on="mgra",
            ).dissolve(by="taz", as_index=False)
            update_taz["taz_label"] = update_taz["taz"].map(
                lambda n: "Updated TAZ {}".format(int(n))
            )

        # Create HTML map to visualize these changes
        update_map = folium.Map(
            location=[
                self.mgra_full[self.mgra_full.MGRA.isin(self.inupdate.MGRA.unique())]
                .iloc[0]["y"]
                .item(),
                self.mgra_full[self.mgra_full.MGRA.isin(self.inupdate.MGRA.unique())]
                .iloc[0]["x"]
                .item(),
            ],
            zoom_start=15,
            tiles="cartodbpositron",
        )
        loc = "Land Use Updates"
        title_html = """
                     <h3 align="center" style="font-size:16px"><b>{}</b></h3>
                     """.format(
            loc
        )

        update_map.get_root().html.add_child(folium.Element(title_html))
        emp_group = FeatureGroup(name="Employment Adjustment", show=True)
        emp_group2 = FeatureGroup(name="Employment Total", show=False)
        hh_group = FeatureGroup(name="Households Adjustment", show=False)
        hh_group2 = FeatureGroup(name="Households Total", show=False)
        gq_group = FeatureGroup(name="Group Quarters Adjustment", show=False)
        gq_group2 = FeatureGroup(name="Group Quarters Total", show=False)
        enrl_group = FeatureGroup(name="Enrollment Adjustment", show=False)
        enrl_group2 = FeatureGroup(name="Enrollment Total", show=False)
        hotel_group = FeatureGroup(name="Hotel Rooms Adjustment", show=False)
        hotel_group2 = FeatureGroup(name="Hotel Rooms Total", show=False)
        park_group = FeatureGroup(name="Park Acres Adjustment", show=False)
        park_group2 = FeatureGroup(name="Park Acres Total", show=False)
        beach_group = FeatureGroup(name="Beach Acres Adjustment", show=False)
        beach_group2 = FeatureGroup(name="Beach Acres Total", show=False)
        ops_group = FeatureGroup(
            name="Open Space/Park/Preserve Acres Adjustment", show=False
        )
        ops_group2 = FeatureGroup(
            name="Open Space/Park/Preserve Acres Total", show=False
        )
        duden_group = FeatureGroup(name="DU Density", show=False)
        empden_group = FeatureGroup(name="Employment Density", show=False)
        maz_boundary_group = FeatureGroup(name="MGRA Boundary", show=False)
        duden_label_layer = FeatureGroup(name="Dwelling Unit Density Label", show=False)
        intaz_boundary_group = FeatureGroup(name="Original TAZ Boundary", show=False)
        outtaz_boundary_group = FeatureGroup(name="Updated TAZ Boundary", show=False)
        self.add_choro_group(
            update_map,
            self.emp_update,
            emp_group,
            "Employees Adjustment",
            "emp_total",
            "YlOrRd",
        )
        self.add_choro_group(
            update_map,
            self.compare_emp,
            emp_group2,
            "Employees Total",
            "emp_total_update",
            "YlOrRd",
        )
        self.add_choro_group(
            update_map, self.housing, hh_group, "Housing Adjustment", "hh", "YlOrRd"
        )
        self.add_choro_group(
            update_map,
            self.compare_housing,
            hh_group2,
            "Housing Total",
            "hh_update",
            "YlOrRd",
        )
        self.add_choro_group(
            update_map,
            self.gq_pop,
            gq_group,
            "Group Quarters Adjustment",
            "Beds",
            "YlOrRd",
        )
        self.add_choro_group(
            update_map,
            self.compare_gqs,
            gq_group2,
            "Group Quarters Total",
            "tot_gq_update",
            "YlOrRd",
        )
        self.add_choro_group(
            update_map,
            self.enrollment,
            enrl_group,
            "Enrollment Adjustment",
            "tot_enroll",
            "YlOrRd",
        )
        self.add_choro_group(
            update_map,
            self.compare_enrollment,
            enrl_group2,
            "Enrollment Total",
            "tot_enroll_update",
            "YlOrRd",
        )
        self.add_choro_group(
            update_map,
            self.hotels,
            hotel_group,
            "Hotel Rooms Adjustment",
            "hotelroomtotal",
            "YlOrRd",
        )
        self.add_choro_group(
            update_map,
            self.compare_hotel,
            hotel_group2,
            "Hotel Rooms Total",
            "hotelroomtotal_update",
            "YlOrRd",
        )
        self.add_choro_group(
            update_map,
            self.parks,
            park_group,
            "Park Acres Adjustment",
            "parkactive",
            "YlOrRd",
            acre=True,
        )
        self.add_choro_group(
            update_map,
            self.compare_acre,
            park_group2,
            "Park Acres Total",
            "parkactive_update",
            "YlOrRd",
            acre=True,
        )
        self.add_choro_group(
            update_map,
            self.beach,
            beach_group,
            "Beach Acres Adjustment",
            "beachactive",
            "YlOrRd",
            acre=True,
        )
        self.add_choro_group(
            update_map,
            self.compare_acre,
            beach_group2,
            "Beach Acres Total",
            "beachactive_update",
            "YlOrRd",
            acre=True,
        )
        self.add_choro_group(
            update_map,
            self.openspace,
            ops_group,
            "Open Space Acres Adjustment",
            "openspaceparkpreserve",
            "YlOrRd",
            acre=True,
        )
        self.add_choro_group(
            update_map,
            self.compare_acre,
            ops_group2,
            "Open Space Acres Total",
            "openspaceparkpreserve_update",
            "YlOrRd",
            acre=True,
        )
        self.add_choro_group(
            update_map,
            self.density_change[self.density_change.changed_empden].rename(
                columns={"mgra": "MGRA"}
            ),
            empden_group,
            "Employment Density",
            "empden_out",
            "Purples",
            density=True,
        )
        self.add_choro_group(
            update_map,
            self.density_change[self.density_change.changed_duden].rename(
                columns={"mgra": "MGRA"}
            ),
            duden_group,
            "Dwelling Unit Density",
            "duden_out",
            "Greens",
            density=True,
        )

        # add_boundary_group(update_map, self.mgra_full, maz_boundary_group, '#006fa1','MGRA')

        if self.to_update_taz:
            self.add_boundary_group(
                update_map, orig_taz, intaz_boundary_group, "#63af5e", "taz"
            )
            self.add_boundary_group(
                update_map, update_taz, outtaz_boundary_group, "#f68b1f", "taz"
            )

        folium.LayerControl(collapsed=False).add_to(update_map)
        # show employment
        f = folium.Figure(width=1800, height=900)
        m = update_map.add_to(f)

        div = Div(text=m._repr_html_())

        layout2 = column(div)
        tab2 = TabPanel(child=layout2, title="Map")
        tabs = Tabs(tabs=[tab1, tab2])
        output_file(_join(self.outdir, "landuse_updates.html"))
        save(tabs)


if __name__ == "__main__":
    luc = LUConverter(sys.argv[1])
    luc()
