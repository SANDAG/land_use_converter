# -*- coding: utf-8 -*-
"""
Created on Mon May 9 10:13:16 2022
Save Original Inputs for SANDAG ABM2+ Enhancement plan
@author: hannah.carson

saves original inputs in case of multiple scenarios or re-runs


"""

import pandas as pd
import numpy as np
import shutil,os
import sys
import warnings


warnings.filterwarnings("ignore")  
_join = os.path.join

class PreserveInputs(object):

    def __init__(self,dir1):
        self.no_build_dir = dir1
        self.model_dir_properties = {}
        
    def __call__(self):
        self.read_inputs()
        self.preserve_files()
        
        
    def read_inputs(self):
        """ Read property file in the abm release directory and the model directory """
        with open(_join(self.no_build_dir,'conf','sandag_abm.properties'),'r') as f:
            hold = 1
            props = f.readlines()
            for prop in props:
                prop = prop.rstrip()
                if prop.startswith('#') or len(prop.split('=')) < 2:
                    self.model_dir_properties[hold] = None
                    hold += 1
                else:
                    self.model_dir_properties[prop.split('=')[0].replace(' ','')] = prop.split('=')[1].replace(' ','')
        f.close()
    
        
        
    def preserve_files(self):
        """ save files that may be edited for future use """
        for year in ['',2020,2025,2035,2050]:
            shutil.copy(_join(self.no_build_dir,'uec','CrossBorderDestinationChoiceSoaAlternatives{}.csv'.format(year)),_join(self.no_build_dir,'uec','original','CrossBorderDestinationChoiceSoaAlternatives{}.csv'.format(year)))
        shutil.copy(_join(self.no_build_dir,self.model_dir_properties['taz.terminal.time.file']),_join(self.no_build_dir,'input','original',self.model_dir_properties['taz.terminal.time.file']))
        shutil.copy(_join(self.no_build_dir,'uec','SoaTazDistAlts.csv'),_join(self.no_build_dir,'uec','original','SoaTazDistAlts.csv'))
        shutil.copy(_join(self.no_build_dir,'uec','TourDcSoaDistanceAlts.csv'),_join(self.no_build_dir,'uec','original','TourDcSoaDistanceAlts.csv'))
        shutil.copy(_join(self.no_build_dir,'conf','sandag_abm.properties'),_join(self.no_build_dir,'conf','original','sandag_abm.properties'))
        shutil.copy(_join(self.no_build_dir,'conf','cvm.properties'),_join(self.no_build_dir,'conf','original','cvm.properties'))
        shutil.copy(_join(self.no_build_dir,self.model_dir_properties[r'mgra.socec.file']),_join(self.no_build_dir,'input','original',self.model_dir_properties[r'mgra.socec.file']))
        files = ['tazcentroids_cvm.csv','hwycov.e00','LINKTYPETURNS.DBF','LINKTYPETURNSCST.DBF','special_fares.txt','tap.ptype','tapcov.dbf','timexfer_AM.csv','timexfer_MD.csv','timexfer_PM.csv','timexfer_EV.csv','timexfer_EA.csv','trcov.e00','trlink.csv','trrt.csv','trstop.csv','turns.csv','SANDAG_Bike_Net.dbf','SANDAG_Bike_Node.dbf']
        for f in files:
            shutil.copy(_join(self.no_build_dir,'input',f),_join(self.no_build_dir,'input','original','input'))    
if __name__ == "__main__":
    pc = PreserveInputs(sys.argv[1])
    pc()        
        
    
