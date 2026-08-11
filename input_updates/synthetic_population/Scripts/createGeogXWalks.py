import pandas as pd
import sys
import os
import numpy as np

parameters_file = sys.argv[1]

parameters = pd.read_csv(parameters_file)
parameters.columns = ['Key', 'Value']
WORKING_DIR = parameters[parameters.Key == 'WORKING_DIR']['Value'].item().strip(' ')


taz_puma = pd.read_csv(os.path.join(WORKING_DIR,'setup','data','taz_puma_xwalk.csv'))
# if os.path.isfile(os.path.join(WORKING_DIR,'..','taz_split','mgra_taz_correspondence.csv')):
    # mgra_taz    = pd.read_csv(os.path.join(WORKING_DIR,'..','taz_split','mgra_taz_correspondence.csv'))
# else:
mdldir          = parameters[parameters.Key == 'MODEL_DIR']['Value'].item().strip(' ')
properties = {}
with open(os.path.join(mdldir,'conf','sandag_abm.properties'),'r') as f:
        props = f.readlines()
        for prop in props:
            prop = prop.rstrip()
            if prop.startswith('#') or len(prop.split('=')) < 2:
                continue
            else:
                properties[prop.split('=')[0].replace(' ','')] = prop.split('=')[1].replace(' ','')
f.close()    
    
mgra_taz = pd.read_csv(os.path.join(WORKING_DIR,'..','2_landuse_converter','outputs', properties['mgra.socec.file'].split('/')[1]), usecols = ['mgra','taz'])
    # mgra_taz  = pd.read_csv(os.path.join(mdldir, properties['mgra.socec.file']), usecols = ['mgra','taz'])
mgra_taz.columns = ['MAZ', 'TAZ']
if os.path.isfile(os.path.join(WORKING_DIR,'..','1_taz_split','outputs','split_tazs.csv')):
    split_tazs = pd.read_csv(os.path.join(WORKING_DIR,'..','1_taz_split','outputs','split_tazs.csv'))
    mgra_taz_old = mgra_taz[~mgra_taz.TAZ.isin(split_tazs.new_taz.unique())]
    mgra_taz_new = mgra_taz[mgra_taz.TAZ.isin(split_tazs.new_taz.unique())]
    mgra_taz_old = mgra_taz_old.merge(taz_puma, how = 'left', on = 'TAZ').drop_duplicates()#.astype(np.int64)
    mgra_taz_new = mgra_taz_new.merge(split_tazs, left_on = 'TAZ', right_on = 'new_taz')
    mgra_taz_new = mgra_taz_new.merge(taz_puma, how = 'left', left_on = 'orig_taz', right_on = 'TAZ', suffixes = ['','taz_puma'])
    mgra_taz_new = mgra_taz_new[mgra_taz_old.columns].drop_duplicates()
    mgra_taz_new = mgra_taz_new.astype(np.int64)
    pd.concat([mgra_taz_old,mgra_taz_new]).sort_values('MAZ').to_csv(os.path.join(WORKING_DIR,'setup','data','geo_crosswalks.csv'),index = False)

else:
    mgra_taz.merge(taz_puma, how = 'left', on = 'TAZ').drop_duplicates().astype(np.int64).to_csv(os.path.join(WORKING_DIR,'setup','data','geo_crosswalks.csv'),index = False)
