import pandas as pd
import sys
import os
import shutil
import numpy as np

parameters_file = sys.argv[1]
properties = {}
parameters = pd.read_csv(parameters_file)
parameters.columns = ['Key', 'Value']
WORKING_DIR = parameters[parameters.Key == 'WORKING_DIR']['Value'].item().strip(' ')
MODEL_DIR   =      parameters[parameters.Key == 'MODEL_DIR']['Value'].item().strip(' ')
override   =      parameters[parameters.Key == 'OVERRIDE']['Value'].item().strip(' ')
override_file   =      parameters[parameters.Key == 'OVERRIDE_FILE']['Value'].item().strip(' ')
with open(os.path.join(MODEL_DIR,'conf','sandag_abm.properties'),'r') as f:
    props = f.readlines()
    for prop in props:
        prop = prop.rstrip()
        if prop.startswith('#') or len(prop.split('=')) < 2:
            continue
        else:
            properties[prop.split('=')[0].replace(' ','')] = prop.split('=')[1].replace(' ','')
f.close()
lu = pd.read_csv(os.path.join(WORKING_DIR,'..','2_landuse_converter','outputs', properties['mgra.socec.file'].split('/')[1]))
project = pd.read_excel(override_file,sheet_name = 'Project_Data').dropna(subset = ['MGRA']).MGRA.unique()
# lu = pd.read_csv(os.path.join(WORKING_DIR,'..','..','LUConverter','outputs', properties['mgra.socec.file'].split('/')[1]))
lucols = lu.columns

has_hh = False
has_gq = False
has_neg = False
if os.path.isfile(os.path.join(WORKING_DIR,'..','2_landuse_converter','outputs','temp','has_hh.txt')):
    has_hh = True
if os.path.isfile(os.path.join(WORKING_DIR,'..','2_landuse_converter','outputs','temp','has_gq.txt')):
    has_gq = True
if os.path.isfile(os.path.join(WORKING_DIR,'..','2_landuse_converter','outputs','temp','negative_pop.txt')):
    has_neg = True

orig_hh = pd.read_csv(os.path.join(MODEL_DIR,'input','original',properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile']))
    
if not has_hh and not has_gq and not has_neg:
    shutil.copy(os.path.join(WORKING_DIR,'..','2_landuse_converter','outputs',properties['mgra.socec.file'].split('/')[1]), os.path.join(WORKING_DIR,'..','4_final_lu_updates','outputs',properties['mgra.socec.file'].split('/')[1]))
    sys.exit()
    
if has_hh or has_gq:
    hh = pd.read_csv(os.path.join(WORKING_DIR,'..','3_synthetic_population','setup','output','combined','households.csv'))
    pop = pd.read_csv(os.path.join(WORKING_DIR,'..','3_synthetic_population','setup','output','combined','persons.csv'))
else:
    hh = pd.read_csv(os.path.join(MODEL_DIR,'input','original',properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile']))
    pop = pd.read_csv(os.path.join(MODEL_DIR,'input','original',properties['PopulationSynthesizer.InputToCTRAMP.PersonFile']))
if has_neg:
    hhcols = hh.columns
    popcols = pop.columns
    mgra_changes = pd.read_csv(os.path.join(WORKING_DIR,'..','2_landuse_converter','outputs','temp','mgra_changes.csv'))
    if override == "YES":
        remove_hh = mgra_changes[mgra_changes.hh ==0].mgra.unique()
        hh = hh[~hh.mgra.isin(remove_hh)]
        pop = pop[pop.hhid.isin(hh.hhid.unique())]
    else:
        remove_hh = mgra_changes[mgra_changes.hh <0][['mgra','hh','hh_sf','hh_mf','hh_mh']]
        for idx,row in remove_hh.iterrows():
            mgra = row['mgra']
            num_hh = abs(row['hh'])
            
            bldgsz_dict = {'hh_sf':[2,3],'hh_mf':[4,5,6,7,8,9],'hh_mh':[1]}
            for key,value in bldgsz_dict.items():
                num_hh = abs(row[key])
                if num_hh == 0:
                    continue
                else:
                    removal_df = hh[(hh.mgra == mgra) & (hh.bldgsz.isin(value))]
                    if len(removal_df) < num_hh:
                        print("WARNING: MGRA {} does not have {} {} to remove. Will remove from total households".format(mgra, num_hh, key))
                        additional = num_hh - len(removal_df)
                        removal_df = removal_df.append(hh[(hh.mgra == mgra) & (~hh.bldgsz.isin(value))].sample(additional))
                    removal_id = removal_df.sample(num_hh).hhid.unique()
                    if len(removal_id) != num_hh:
                        print("ERROR: Oversampled households for removal")
                    hh = hh[~hh.hhid.isin(removal_id)]
                    pop = pop[~pop.hhid.isin(removal_id)]
    hh['hhid_new'] = np.arange(1,len(hh)+1)
    pop = pop.merge(hh[['hhid','hhid_new']], how = 'left', on = 'hhid')
    pop = pop.drop('hhid',axis=1).rename(columns ={'hhid_new':'hhid'})[popcols]
    hh = hh.drop('hhid',axis =1).rename(columns={'hhid_new':'hhid'})[hhcols]
    hh.to_csv(os.path.join(WORKING_DIR,'..','4_final_lu_updates','outputs',properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile'].split(r'/')[1]),index = False) 
    pop.to_csv(os.path.join(WORKING_DIR,'..','4_final_lu_updates','outputs',properties['PopulationSynthesizer.InputToCTRAMP.PersonFile'].split(r'/')[1]),index = False) 
hh = hh[hh.unittype == 0]
incbins = [-99999,15000,30000,45000,60000,75000,100000,125000,150000,200000,hh.hinc.max()+1]
hh['hincbin'] = pd.cut(hh.hinc, incbins, labels = False)

#hhp
lu = lu.merge(hh.groupby('mgra',as_index = False)[['persons']].sum().rename(columns = {'persons':'hhp'}), how = 'left', on = 'mgra',suffixes = ['','_update'])
lu.loc[lu.mgra.isin(project),'hhp'] = lu.loc[lu.mgra.isin(project)]['hhp_update']
lu.loc[lu.mgra.isin(project),'hhp'] = lu.loc[lu.mgra.isin(project),'hhp'].fillna(0)
#pop
lu.loc[lu.mgra.isin(project),'pop'] = lu.loc[lu.mgra.isin(project)]['hhp'] + lu.loc[lu.mgra.isin(project)]['gq_mil'] + lu.loc[lu.mgra.isin(project)]['gq_civ']
#hhs
lu.loc[lu.mgra.isin(project),'hhs'] = lu.loc[lu.mgra.isin(project),'hhp']/lu.loc[lu.mgra.isin(project),'hh']
lu.loc[(lu.mgra.isin(project)) & (lu.hh ==0),'hhs'] = 0
#incbins
hh = hh.groupby(['mgra','hincbin'],as_index = False)[['hhid']].count().pivot(index = 'mgra',columns = 'hincbin',values = 'hhid')
hh = hh.fillna(0)
inccols = ['i{}'.format(i) for i in range(1,11)]

hh.columns = inccols
lu = lu.merge(hh.reset_index(), how = 'left', on = 'mgra', suffixes = ['','_update'])

lu.loc[lu.mgra.isin(project),inccols] = lu.loc[lu.mgra.isin(project)][['{}_update'.format(col) for col in inccols]].fillna(0).to_numpy()
hh = hh.reset_index()
lu = lu.drop(['{}_update'.format(col) for col in inccols] + ['hhp_update'],axis = 1)

lu.loc[lu.mgra.isin(project),inccols] = lu.loc[lu.mgra.isin(project)][inccols].astype(np.int64)
lu = lu.fillna(0)
#check data types match
orig_lu = pd.read_csv(os.path.join(MODEL_DIR,properties['mgra.socec.file']))
for x in orig_lu.columns:
    lu[x]=lu[x].astype(orig_lu[x].dtypes.name)
lu.to_csv(os.path.join(WORKING_DIR,'..','4_final_lu_updates','outputs',properties['mgra.socec.file'].split('/')[1]),index = False)
# lu.fillna(0).to_csv(os.path.join(MODEL_DIR,'..','Build',properties['mgra.socec.file'],index = False))