# -*- coding: utf-8 -*-
"""
Created on Mon May 9 10:13:16 2022
Update model files in case of a zone split
@author: hannah.carson




"""

import pandas as pd
import numpy as np
import shutil,os
import sys
import warnings


warnings.filterwarnings("ignore")  
_join = os.path.join

class TAZSplitUpdater(object):

    def __init__(self, working_directory,model_directory, no_build_directory, taz_split_dir):
        self.properties = {}
        self.working_directory = working_directory
        self.model_directory = model_directory
        self.no_build_directory = no_build_directory
        self.taz_split_dir = taz_split_dir
        self.has_splits = False
        self.mgra_taz = pd.DataFrame()
        
    def __call__(self):
        self.read_inputs()
        self.update_properties()
        self.update_inputs()
        self.copy_files()
        
    def read_inputs(self):    
        """ Read inputs for the tool """
        with open(_join(self.model_directory,'conf','sandag_abm.properties'),'r') as f:
            props = f.readlines()
            for prop in props:
                prop = prop.rstrip()
                if prop.startswith('#') or len(prop.split('=')) < 2:
                    continue
                else:
                    self.properties[prop.split('=')[0].replace(' ','')] = prop.split('=')[1].replace(' ','')
        f.close()
        try:
            self.mgra_taz    = pd.read_csv(_join(self.working_directory,'..','..','network_build','data','mgra_zone.csv'))
            self.mgra_taz.columns = [col.replace(" ","") for col in self.mgra_taz.columns]
            self.has_splits = True
            print("new max taz: {}".format(self.mgra_taz.taz.max()))
            if self.mgra_taz.taz.max() == 4996:
                self.has_splits = False
                print("No TAZ Split Detected")
        except:
            print("No TAZ Split Detected")

        
    def update_properties(self):
        """ Update property file"""
        if self.has_splits:
            sandag_props =  open(_join(self.no_build_directory,'conf', 'original','sandag_abm.properties'),"r")
            props = sandag_props.readlines()
            sandag_props.close()
            for i,line in enumerate(props):
                if line.startswith('zones.count'):
                    props[i] = "zones.count = {}\n".format(int(self.mgra_taz.taz.max()))
            sandag_props =  open(_join(self.working_directory,'outputs','conf','sandag_abm.properties'),"w")
            sandag_props.writelines(props)
            sandag_props.close()

            cvm_props =  open(_join(self.no_build_directory,'conf','original','cvm.properties'),"r")
            cvmprops = cvm_props.readlines()
            cvm_props.close()
            for i,line in enumerate(cvmprops):
                if line.startswith('EndZone'):
                    cvmprops[i] = "EndZone={}\n".format(int(self.mgra_taz.taz.max()))
            cvm_props =  open(_join(self.working_directory,'outputs','conf','cvm.properties'),"w")
            cvm_props.writelines(cvmprops)
            cvm_props.close()
        
       
    def update_inputs(self):
        """ update relevant inputs"""
        
        if self.has_splits:
            orig_correspondence = pd.read_csv(_join(self.no_build_directory,'input','original',self.properties[r'mgra.socec.file']), usecols = ['mgra','taz'])
            assert len(self.mgra_taz) == len(orig_correspondence), "new zone system is not compatible with baseline scenario"
            new_tazs = [taz for taz in self.mgra_taz.taz.unique() if taz not in orig_correspondence.taz.unique()]
            new_tazs.sort()
            orig_corr = orig_correspondence.groupby('taz',as_index = False).count()
            orig_corr = orig_corr.merge(self.mgra_taz.groupby('taz',as_index = False).count(), how = 'outer', on = 'taz', suffixes = ['_count','_new_count'])
            split_tazs = orig_corr[(orig_corr.mgra_count != orig_corr.mgra_new_count) & orig_corr.mgra_count >0].taz.unique()
            split_dict_a = {}
            split_dict_b = {}
            for taz in new_tazs:
                beacon_maz = self.mgra_taz[self.mgra_taz.taz == taz].mgra.unique()[0]
                orig_taz = orig_correspondence.loc[orig_correspondence.mgra == beacon_maz].taz.unique()[0]
                split_dict_a[orig_taz] = taz
                split_dict_b[taz] = orig_taz
            # update uecs
            pd.DataFrame(list(split_dict_b.items()),columns = ['new_taz','orig_taz']).to_csv(_join(self.working_directory,'outputs','split_tazs.csv'),index = False)
            for year in ['',2020,2025,2035,2050]:
                uec_file_orig = _join(self.no_build_directory,'uec','original','CrossBorderDestinationChoiceSoaAlternatives{}.csv'.format(year))
                uec_file_update = _join(self.working_directory, 'outputs','uec','CrossBorderDestinationChoiceSoaAlternatives{}.csv'.format(year))
                uec = pd.read_csv(uec_file_orig)
                for i,taz in enumerate(new_tazs):
                    vals = uec.loc[uec.dest == split_dict_b[taz]].copy()
                    vals['a'] = range(uec.a.max()+1, len(vals) +uec.a.max() +1)
                    vals['dest'] = taz
                    uec = pd.concat([uec,vals])
                uec = uec.sort_values(['poe','dest'])
                uec['a'] = np.arange(1,len(uec)+1)
                uec.to_csv(uec_file_update,index = False)
            
            uec_file_orig = _join(self.no_build_directory,'uec','original','SoaTazDistAlts.csv')
            uec_file_update = _join(self.working_directory,'outputs','uec','SoaTazDistAlts.csv')
            uec = pd.read_csv(uec_file_orig)
            for newtaz in new_tazs:
                uec = uec.append(pd.Series({'a':newtaz,'dest':newtaz}),ignore_index = True)
            uec.to_csv(uec_file_update,index = False)
            
            uec_file_orig = _join(self.no_build_directory,'uec','original','TourDcSoaDistanceAlts.csv')
            uec_file_update = _join(self.working_directory,'outputs','uec','TourDcSoaDistanceAlts.csv')
            uec = pd.read_csv(uec_file_orig)
            for newtaz in new_tazs:
                uec = uec.append(pd.Series({'a':newtaz,'dest':newtaz}),ignore_index = True)
            uec.to_csv(uec_file_update,index = False)
            
            # update zone.term
            zone_term = pd.read_fwf(_join(self.no_build_directory,'input','original',self.properties['taz.terminal.time.file']), header = None, widths = [5,7])
            zone_term.columns = ['zone','terminal']
            new_lines = []
            for split_taz in split_tazs:
                if split_taz in zone_term.zone.unique():
                    terminal_val = zone_term.loc[zone_term.zone == split_taz].terminal.item()
                    zone_digits = len(str(split_dict_a[split_taz]))
                    terminal_digits = len(str(terminal_val))
                    zone_spaces = 5-zone_digits
                    terminal_spaces = 7-terminal_digits
                    new_lines.append(' '*zone_spaces + '{}'.format(split_dict_a[split_taz]) + ' '*terminal_spaces +'{}\n'.format(terminal_val))
            
            zone_term_read =  open(_join(self.no_build_directory,'input','original',self.properties['taz.terminal.time.file']),"r")
            orig_zone_term = zone_term_read.readlines()
            new_zone_term = orig_zone_term + new_lines
            new_zone_term_write = open(_join(self.working_directory,'outputs',self.properties['taz.terminal.time.file']),"w")
            new_zone_term_write.writelines(new_zone_term)
            zone_term_read.close()
            new_zone_term_write.close()
            
            #update taz centroids
            taz_centroid = pd.read_csv(_join(self.no_build_directory,'input','original','input','tazcentroids_cvm.csv'))
            for new_taz in new_tazs:
                taz = new_taz
                orig_taz = split_dict_b[taz]
                new_seg = taz_centroid[taz_centroid.taz == orig_taz].copy()
                new_seg['taz'] = taz
                taz_centroid = taz_centroid.append(new_seg,ignore_index = True)
            taz_centroid.to_csv(_join(self.working_directory,'outputs','input','tazcentroids_cvm.csv'), index = False)
            
            #update land use
            orig_lu = pd.read_csv(_join(self.no_build_directory,'input','original',self.properties[r'mgra.socec.file']))
            orig_lu_cols = orig_lu.columns
            new_lu = orig_lu.drop('taz',axis = 1).merge(self.mgra_taz, how = 'left', on = 'mgra')
            new_lu[orig_lu_cols].to_csv(_join(self.working_directory,'outputs',self.properties[r'mgra.socec.file']),index = False)
            

    def copy_files(self):
        if self.has_splits:
            files = [r'..\data\zone_jur.csv',
            'hwycov.e00',
            'LINKTYPETURNS.DBF',
            'LINKTYPETURNSCST.DBF',
            'modexfer.dbf',
            'special_fares.txt',
            'tap.ptype',
            'tapcov.dbf',
            'timexfer_AM.csv',
            'timexfer_MD.csv',
            'timexfer_PM.csv',
            'timexfer_EV.csv',
            'timexfer_EA.csv',
            'trcov.e00',
            'trlink.csv',
            'trrt.csv',
            'trstop.csv',
            'turns.csv',
            'SANDAG_Bike_Net.dbf',
            'SANDAG_Bike_Net.prj',
            'SANDAG_Bike_Net.sbn',
            'SANDAG_Bike_Net.sbx',
            'SANDAG_Bike_Net.shp',
            'SANDAG_Bike_Net.shx',
            'SANDAG_Bike_Node.dbf',
            'SANDAG_Bike_Node.prj',
            'SANDAG_Bike_Node.sbn',
            'SANDAG_Bike_Node.sbx',
            'SANDAG_Bike_Node.shp',
            'SANDAG_Bike_Node.shx']
            for f in files:
                shutil.copy(_join(self.taz_split_dir,f),_join(self.working_directory,'outputs','input'))    
if __name__ == "__main__":
    TSU = TAZSplitUpdater(sys.argv[1],sys.argv[2], sys.argv[3], sys.argv[4])
    TSU()        
        