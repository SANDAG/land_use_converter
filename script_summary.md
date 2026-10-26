---

## Pipeline Overview

The five folders implement a sequential pipeline that updates SANDAG's ABM2+ land use inputs for a build scenario, then prepares the population and zone files for a model run. Each step depends on outputs from the prior step, and all steps read from `sandag_abm.properties` for key file paths.

---

## Step 1 — TAZ Split (1_taz_split/scripts/taz_split_update.py)

**Class**: `TAZSplitUpdater`  
**Purpose**: Propagates a zone split (new TAZ added by the network team) across all relevant model input files. Only activates if `network_build/data/mgra_zone.csv` exists and its max TAZ exceeds 4,996 (the baseline zone count).

**Changes made when a split is detected:**
- Updates `zones.count` in `sandag_abm.properties` and `EndZone` in `cvm.properties`
- Appends rows for the new TAZ to the Cross-Border Destination Choice SOA alternative files (5 horizon years: blank, 2020, 2025, 2035, 2050)
- Appends rows to `SoaTazDistAlts.csv` and `TourDcSoaDistanceAlts.csv`
- Appends rows to the terminal time file (fixed-width format)
- Duplicates the parent TAZ centroid in `tazcentroids_cvm.csv`
- Replaces the `taz` column in the MGRA socioeconomic file with values from `mgra_zone.csv`
- Copies all network/transit shapefiles and CSVs from the TAZ split directory to outputs
- Saves `split_tazs.csv` mapping new TAZ IDs to their original parent TAZ

**Configuration** (4 command-line arguments):
| Arg | Description |
|-----|-------------|
| `working_directory` | Tool working directory |
| `model_directory` | ABM model directory (contains `conf/sandag_abm.properties`) |
| `no_build_directory` | No-build scenario directory with `conf/original/` and `input/original/` |
| `taz_split_dir` | Directory containing updated network files |

---

## Step 2 — Land Use Converter (2_landuse_converter/scripts/landuse_converter_py3.py)

**Class**: `LUConverter`  
**Purpose**: The core land use update tool. Reads client-provided project data from an Excel file and applies employment, housing, hotel, park/open space, group quarters, and enrollment changes to the MGRA socioeconomic file. Produces QA/QC outputs.

**Processing steps:**
1. **`read_inputs`** — Reads parameters CSV, `sandag_abm.properties`, the MGRA land use CSV, the MGRA shapefile (`SANDAG_MGRA_final.shp`), and the override Excel file. Also reads `LandUseUnitTypes.xlsx` for density specs, allocation shares, unit-type correlations, and LU code correspondences.
2. **`create_density_matrix`** — Converts KSF/acres inputs to employee counts using a priority matrix of density specifications per land use code. Warns if acre input exceeds MGRA area.
3. **`update_employment`** — Distributes total employees to ABM employment sub-categories using allocation shares. Also derives residential-area employment from new dwelling units using a housing/employment ratio stratified by pseudo-MSA. Zeroes out negatives with a warning.
4. **`update_hotels`** — Updates `budgetroom`, `economyroom`, `luxuryroom`, `midpriceroom`, `upscaleroom`, and `hotelroomtotal` using room-type shares from the `HotelRoomShare` sheet.
5. **`update_acre`** — Updates `parkactive`, `openspaceparkpreserve`, and `beachactive` (in acres) by LU code classification.
6. **`update_housing`** — Assigns dwelling units to `hs_sf`, `hs_mf`, `hs_mh`, derives occupied households using CPA-level occupancy rates from the baseline land use file, and tracks an affordable housing (`hh_af`) sub-count. Writes a `has_hh.txt` flag file if any households are added.
7. **`update_gqs`** — Updates `gq_civ` and `gq_mil` from the `Beds` column by LU code. Writes a `has_gq.txt` flag file if group quarters are added.
8. **`update_enrollment`** — Updates K–8, high school, college, other college, and adult school enrollment.
9. **`update_density`** — Recalculates `duden` (dwelling unit density) and `empden` (employment density) using walk distances from `active.logsum.matrix.file.walk.mgra` over a configurable buffer radius.
10. **`save_landuse_updates`** — Writes the updated MGRA CSV and `mgra_changes.csv`. If any MGRA ends up with negative household counts relative to its synthesized population, writes `negative_pop.txt`.
11. **`qa_qc_map`** — Generates interactive choropleth maps (Folium/Bokeh HTML) for employment, housing, hotels, parks, enrollment, and density changes.

**Configuration parameters** (from CSV file, passed as a command-line argument):
| Key | Description |
|-----|-------------|
| `OUTPUT_DIR` | Output directory |
| `INPUT_DIR` | Input directory (contains shapefile and `LandUseUnitTypes.xlsx`) |
| `MODEL_DIR` | ABM model directory |
| `OVERRIDE_LU` | `YES`/`NO` — replace vs. add land use values |
| `OVERRIDE_HH` | `YES`/`NO` — replace vs. add household values |
| `OVERRIDE_EMP` | `YES`/`NO` — replace vs. add employment values |
| `BUFFER` | Buffer radius in miles for density recalculation |
| `OVERRIDE_FILE` | Path to Excel file with `Project_Data` and `HotelRoomShare` sheets |

**Key properties read from `sandag_abm.properties`**: `mgra.socec.file`, `active.logsum.matrix.file.walk.mgra`

---

## Step 3 — Synthetic Population (3_synthetic_population/Scripts/)

Five scripts prepare and run PopulationSim in "repopulation" (repop) mode for the project area only, then merge results.

### createGeogXWalks.py
Builds `setup/data/geo_crosswalks.csv` (MAZ → TAZ → PUMA), which PopulationSim requires. If a TAZ split was detected in step 1, it handles PUMA assignment for new TAZs by mapping through their parent TAZ.

### constructPipe.py
Converts the model's original household/person files into a PopulationSim repop `pipeline.h5` HDF5 file. Splits records into regular households (`unittype=0`) and group quarters (`unittype=1`), writes them into `setup/output/HH/pipeline.h5` and `setup/output/GQ/pipeline.h5`, and zeroes out all non-seed tables using template files from `Data/pipeline_templates/`. Copies the HH pipeline to `setup/output/af/pipeline.h5` for the affordable housing run.

### constructPipeZero.py
Identical in structure to constructPipe.py but produces a "null" pipeline (`pipeline_null.h5`) with only 1 row per table, used as a no-build reference baseline. Does not write synthetic household/person CSVs.

### createControls.py
Generates PopulationSim control totals for each project MGRA by sampling households from geographically similar areas:
- Identifies project MGRAs by housing type (SF, MF, affordable MF, MH, GQ) from the `OVERRIDE_FILE`
- For SF and MF, finds nearby MGRAs where ≥85% of households match the target type; expands the search radius by 0.25 miles until `HHTHRESH` households and `TAZTHRESH` TAZs are found
- For MH and GQ, samples regionally
- Formats control totals with size (1–4+), workers (0–3+), income (5 bins), kids (yes/no), and unit-type breakdowns

**Additional configuration keys**: `HHTHRESH`, `TAZTHRESH`, `OVERRIDE` (YES/NO), `SAMPLE_MGRA` (Python list literal of MGRA groups)

### mergeHHAFGQ.py
Combines PopulationSim outputs from the HH, AF, and GQ runs into a single `combined/households.csv` and `combined/persons.csv`. Filters AF output to only affordable-flagged MGRAs. Reassigns globally-unique sequential `hhid` values and saves per-run ID mapping dictionaries (`HH_hhid_dict.csv`, etc.).

**Configuration parameters** (all scripts share similar keys from CSV):
| Key | Description |
|-----|-------------|
| `MODEL_DIR` | ABM model directory |
| `LU_DIR` | Land use directory (step 2 output root) |
| `XWALK_DIR` / `WORKING_DIR` | PopulationSim working directory |
| `OVERRIDE_FILE` | Excel file with `Project_Data` sheet |

---

## Step 4 — Final Land Use Updates (4_final_lu_updates/scripts/updateLandUse.py)

**Purpose**: Post-PopulationSim cleanup. Reconciles the land use file and household/person files when PopulationSim produced more households than the land use file can support (i.e., a negative-count situation).

**Logic (flag-file driven):**
- **No flags set** → simply copies the step-2 land use output to this step's output folder and exits.
- **`has_hh.txt` or `has_gq.txt`** → loads synthesized households/persons from step 3's combined output instead of the original model files.
- **`negative_pop.txt`** → removes excess households from the synthesized population:
  - `OVERRIDE=YES`: removes all households from any MGRA where `hh=0`
  - `OVERRIDE=NO`: removes households by building type (`hh_sf`, `hh_mf`, `hh_mh`) matching the exact negative delta per MGRA; falls back to any building type if insufficient records of the target type exist. Reassigns sequential `hhid` values across both files.

**Derived MGRA columns recalculated for project MGRAs:**
| Column | Derivation |
|--------|-----------|
| `hhp` | Sum of `persons` from household file |
| `pop` | `hhp + gq_mil + gq_civ` |
| `hhs` | `hhp / hh` (0 if `hh=0`) |
| `i1`–`i10` | Household counts in 10 income bins (<$15k … >$200k) |

Finally, casts all columns to match the original land use file's data types before writing.

**Configuration parameters** (from CSV):
| Key | Description |
|-----|-------------|
| `WORKING_DIR` | Tool working directory |
| `MODEL_DIR` | ABM model directory |
| `OVERRIDE` | `YES`/`NO` — controls household removal strategy |
| `OVERRIDE_FILE` | Excel file with `Project_Data` sheet (identifies project MGRAs) |

**Key properties**: `mgra.socec.file`, `PopulationSynthesizer.InputToCTRAMP.HouseholdFile`, `PopulationSynthesizer.InputToCTRAMP.PersonFile`

---

## Step 5 — Household Sampling (5_hh_sampling/scripts/popsample.py)

**Class**: `PopSampler`  
**Purpose**: Assigns spatially-graduated sample rates to each MGRA so the ABM over-samples households near the project area for more stable results. Produces both build and no-build sampled population files.

**Processing steps:**
1. **`read_params`** — Reads config and resolves which household/person files to use (step 4 truncated output → step 3 combined output → original model files), depending on `RUN_POPSIM` and whether `negative_pop.txt` exists.
2. **`assign_sample`** — Creates two concentric geographic buffers around project MGRAs (`BUFFER1`, `BUFFER2` miles). Assigns three-tier sample rates: `SAMPLE1` for inner buffer, `SAMPLE2` for outer buffer, `SAMPLE3` for all other MGRAs. Saves `mgra_sample_rate_file.csv`.
3. **`runPopSampler`** — Joins sample rates to households, bins households by income (3 bins) and size (4 bins), and samples each MGRA×income×size group using `sample(frac=SampleRate, replace=True)` with a deterministic seed. Adjusts `hhexpfac` to reflect the effective sample rate. Reassigns sequential `hhid` and `perid`. Runs twice — once for the build scenario, once for the no-build scenario.
4. **`no_lu_sample`** — If no land use changes exist, copies original files with `SampleRate=1` for both scenarios.
5. **`create_samplerate_map`** — Generates a Folium choropleth HTML map (`outputs/sample_rate_map.html`) visualizing sample rates by MGRA.
6. **`create_qaqc_summary`** — Generates a QA/QC summary table.

**Configuration parameters** (from CSV):
| Key | Description |
|-----|-------------|
| `WORKING_DIR` | Tool working directory |
| `MODEL_DIR` | ABM model directory |
| `LU_DIR` | Land use directory (contains MGRA shapefile) |
| `RUN_POPSIM` | `YES`/`NO` — whether step 3 was executed |
| `OVERRIDE_FILE` | Excel file with `Project_Data` sheet |
| `BUFFER1` | Inner buffer radius in miles |
| `BUFFER2` | Outer buffer radius in miles |
| `SAMPLE1` | Sample rate for inner buffer (e.g., `2.0` = 200%) |
| `SAMPLE2` | Sample rate for outer buffer |
| `SAMPLE3` | Background sample rate for the rest of the region |

---

## Cross-Cutting Dependencies

The pipeline uses several sentinel flag files written by step 2 to `2_landuse_converter/outputs/temp/` to coordinate conditional logic across steps 3–5:

| Flag file | Meaning |
|-----------|---------|
| `no_lu.txt` | No land use changes in client input; skip PopulationSim and sampling |
| `has_hh.txt` | New residential households added; PopulationSim HH run is needed |
| `has_gq.txt` | New group quarters added; PopulationSim GQ run is needed |
| `negative_pop.txt` | A project MGRA has fewer households than its synthesized population; trimming needed in step 4 |

All scripts parse `sandag_abm.properties` at runtime, making `mgra.socec.file`, `PopulationSynthesizer.InputToCTRAMP.HouseholdFile`, and `PopulationSynthesizer.InputToCTRAMP.PersonFile` the most critical model configuration properties across the pipeline.
