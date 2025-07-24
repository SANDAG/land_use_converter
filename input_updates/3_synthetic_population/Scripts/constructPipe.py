"""Script to convert existing population and household files to a pipeline hdf5 file
   to be used for the repop feature of PopulationSim"""
   
   
import pandas as pd
import os
import numpy as np
import sys
import ast
import warnings
from shutil import copyfile
_join = os.path.join

warnings.filterwarnings("ignore")  


class RepopFeature(object):

    def __init__(self, params):
        self.popsim_dir =        os.getcwd()
        self.parameters =        pd.DataFrame()
        self.households =        pd.DataFrame()
        self.xwalk      =        pd.DataFrame()
        self.persons    =        pd.DataFrame()
        self.mdldir     =        ''
        self.ludir      =        ''
        self.wdir       =        ''
        self.properties =        {}
        self.mgra_lists =        []
        self.params     =        params
        self.maz_file   =        None
    
    def __call__(self):
        self.read_inputs()
        self.construct_pipe()
        
    def read_inputs(self):    
        self.parameters =        pd.read_csv(self.params)
        self.mdldir     =        self.parameters[self.parameters.Key == 'MODEL_DIR']['Value '].item().strip(' ')
        self.ludir      =        self.parameters[self.parameters.Key == 'LU_DIR']['Value '].item().strip(' ') 
        self.wdir       =        self.parameters[self.parameters.Key == 'XWALK_DIR']['Value '].item().strip(' ') 
        
        self.xwalk      = pd.read_csv(_join(self.popsim_dir,'setup','data','geo_crosswalks.csv'))
        self.persons    = pd.read_csv(_join(self.mdldir,'input','original','input','persons.csv')).rename(columns = {'hhid':'hh_id'})
        self.households = pd.read_csv(_join(self.mdldir,'input','original','input','households.csv')).rename(columns = {'hhid':'hh_id'})
        
    
    def construct_pipe(self):    
        # households = households.set_index('hh_id')
        pipehouseholds = self.households.merge(self.xwalk[['MAZ','PUMA']].rename(columns = {'MAZ':'mgra'}), how = 'left', on = 'mgra')
        pipehouseholds['weight'] = 1
        pipehouseholds['GQWGTP'] = 1
        store = pd.HDFStore(_join(self.popsim_dir,'setup','output','HH','pipeline.h5'))
        store_gq = pd.HDFStore(_join(self.popsim_dir,'setup','output','GQ','pipeline.h5'))

        orig_pipe_file = _join(self.popsim_dir,'Data','pipeline_templates','pipeline.h5')
        orig_pipe_gq_file = _join(self.popsim_dir,'Data','pipeline_templates','pipeline_gq.h5')
        orig_pipe = pd.io.pytables.HDFStore(orig_pipe_file)
        orig_pipe_gq = pd.io.pytables.HDFStore(orig_pipe_gq_file)
        hh = pipehouseholds[pipehouseholds.unittype == 0]
        gq = pipehouseholds[pipehouseholds.unittype == 1]
        gq['TYPE'] = 3
        gq['REGION'] = 4
        gq['STATE'] = 6
        persons = self.persons[self.persons.hh_id.isin(hh.hh_id.unique())]
        gq_persons = self.persons[self.persons.hh_id.isin(gq.hh_id.unique())]
        #in case no update to hh needed
        hh_out = hh.rename(columns = {'mgra':'MAZ','taz':'TAZ'})[['PUMA','TAZ','MAZ','hh_id','persons','hinc','hworkers']]
        hh_out['household_id'] = np.arange(1,len(hh)+1)
        hh_persons_out = persons[['hh_id','perid','age']].merge(hh_out[['hh_id','household_id','PUMA','TAZ','MAZ']], how = 'left', on = 'hh_id')
        #in case no update to gq needed
        if not os.path.exists(_join(self.ludir,'outputs','temp','has_hh.txt')):          
            hh_out.to_csv(_join(self.popsim_dir,'setup','output','HH','synthetic_households.csv'),index = False)
            hh_persons_out[['PUMA','TAZ','MAZ','hh_id','household_id','perid','age']].to_csv(_join(self.popsim_dir,'setup','output','HH','synthetic_persons.csv'),index = False)
        gq_out = gq.rename(columns = {'mgra':'MAZ','taz':'TAZ'})[['PUMA','TAZ','MAZ','hh_id','persons','hinc','hworkers']]
        gq_out['household_id'] = np.arange(1,len(gq)+1)
        if not os.path.exists(_join(self.ludir,'outputs','temp','has_gq.txt')):
            gq_out.to_csv(_join(self.popsim_dir,'setup','output','GQ','synthetic_households.csv'),index = False)
            gq_persons_out = gq_persons[['hh_id','perid','age']].merge(gq_out[['hh_id','household_id','PUMA','TAZ','MAZ']], how = 'left', on = 'hh_id')
            gq_persons_out[['PUMA','TAZ','MAZ','hh_id','household_id','perid','age']].to_csv(_join(self.popsim_dir,'setup','output','GQ','synthetic_persons.csv'),index = False)
        store[r'/persons/setup_data_structures'] = persons #.to_hdf(os.path.join(indir,'pipeline.h5'),key = '/self.persons/setup_data_structures',mode = 'w', format = 'table')
        store[r'/households/setup_data_structures'] = hh.set_index('hh_id') #.to_hdf(os.path.join(indir,'pipeline.h5'),key='/self.households/setup_data_structures',mode = 'a', format = 'table')
        store[r'/expanded_household_ids/expand_households'] = hh[['PUMA','taz','mgra','hh_id']].rename(columns = {'taz':'TAZ','mgra':'MAZ'})
        store_gq[r'/persons/setup_data_structures'] = gq_persons #.to_hdf(os.path.join(indir,'pipeline.h5'),key = '/self.persons/setup_data_structures',mode = 'w', format = 'table')
        store_gq[r'/households/setup_data_structures'] = gq.set_index('hh_id') #.to_hdf(os.path.join(indir,'pipeline.h5'),key='/self.households/setup_data_structures',mode = 'a', format = 'table')
        store_gq[r'/expanded_household_ids/expand_households'] = gq[['PUMA','taz','mgra','hh_id']].rename(columns = {'taz':'TAZ','mgra':'MAZ'})
        #populate empty tables
        orig_pipe_tables = [key for key in orig_pipe.keys()]
        orig_pipe_gq_tables = [key for key in orig_pipe_gq.keys()]
        
        """[r'/MAZ_control_data/input_pre_processor',
            r'/MAZ_controls/setup_data_structures',
            r'/MAZ_weights/sub_balancing.geography=MAZ',
            r'/MAZ_weights_sparse/sub_balancing.geography=MAZ',
            r'/PUMA_controls/setup_data_structures',
            r'/PUMA_weights/final_seed_balancing',
            r'/PUMA_weights/initial_seed_balancing',
            r'/PUMA_weights/integerize_final_seed_weights',
            r'/REGION_control_data/input_pre_processor',
            r'/REGION_controls/setup_data_structures',
            r'/TAZ_control_data/input_pre_processor',
            r'/TAZ_controls/setup_data_structures',
            r'/TAZ_weights/sub_balancing.geography=TAZ',
            r'/TAZ_weights_sparse/sub_balancing.geography=TAZ',
            r'/control_spec/setup_data_structures',
            r'/crosswalk/setup_data_structures',
            r'/household_groups/setup_data_structures',
            r'/households/input_pre_processor',
            r'/incidence_table/setup_data_structures',
            r'/persons/input_pre_processor',
            r'/summary_MAZ/summarize',
            r'/summary_MAZ_PUMA/summarize',
            r'/summary_MAZ_aggregate/summarize',
            r'/summary_REGION_4/summarize',
            r'/summary_TAZ/summarize',
            r'/summary_TAZ_PUMA/summarize',
            r'/summary_TAZ_aggregate/summarize',
            r'/summary_hh_weights/summarize',
            r'/trace_MAZ_weights/sub_balancing.geography=MAZ',
            r'/trace_TAZ_weights/sub_balancing.geography=TAZ']"""
            
        for table in orig_pipe_tables:
            if table in ['/persons/setup_data_structures','/households/setup_data_structures','/expanded_household_ids/expand_households']:
                continue
            tab = orig_pipe[table].copy()
            try:
                for col in tab.columns:
                    tab[col] = 0
                store[table] = tab#.to_hdf(os.path.join(indir,'pipeline.h5'),key = table, mode = 'a', format = 'table')
            except:
                print("MISSING TABLE",table)
        for table in orig_pipe_gq_tables:
            if table in ['/persons/setup_data_structures','/households/setup_data_structures','/expanded_household_ids/expand_households']:
                continue
            
            tab = orig_pipe_gq[table].copy()
            try:
                for col in tab.columns:
                    tab[col] = 0
                store_gq[table] = tab#.to_hdf(os.path.join(indir,'pipeline.h5'),key = table, mode = 'a', format = 'table')
            except:
                print("MISSING TABLE",table)

        dummy_check = pd.read_csv(_join(self.popsim_dir,'Data','pipeline_templates','checkpoints.csv'))
        dummy_check_gq = pd.read_csv(_join(self.popsim_dir,'Data','pipeline_templates','checkpoints_gq.csv'))
        store[r'/checkpoints'] = dummy_check#.to_hdf(os.path.join(indir,'pipeline.h5'),key ='/checkpoints',mode = 'a', format = 'table')
        store_gq[r'/checkpoints'] = dummy_check_gq#.to_hdf(os.path.join(indir,'pipeline.h5'),key ='/checkpoints',mode = 'a', format = 'table')
        self.xwalk = pd.read_csv(_join(self.popsim_dir,'Setup','data','geo_crosswalks.csv'))

        store[r'/geo_cross_walk/input_pre_processor'] = self.xwalk#.to_hdf(os.path.join(indir,'pipeline.h5'),key = '/geo_cross_walk/input_pre_processor', mode = 'a', format = 'table')
        self.xwalk['STATE'] = 6
        store_gq[r'/geo_cross_walk/input_pre_processor'] = self.xwalk#.to_hdf(os.path.join(indir,'pipeline.h5'),key = '/geo_cross_walk/input_pre_processor', mode = 'a', format = 'table')

        store.close()
        store_gq.close()
        orig_pipe.close()
        copyfile(_join(self.popsim_dir,'setup','output','HH','pipeline.h5'),_join(self.popsim_dir,'setup','output','af','pipeline.h5'))
            
        
    
        
if __name__ == "__main__":
    rf = RepopFeature(sys.argv[1])
    rf()