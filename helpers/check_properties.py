# -*- coding: utf-8 -*-
"""
Created on Mon May 9 10:13:16 2022
Property Checker for SANDAG ABM2+ Enhancement plan
@author: hannah.carson

checks the property file is consistent for the abm release


"""

import pandas as pd
import numpy as np
import os
import sys
import warnings


warnings.filterwarnings("ignore")  
_join = os.path.join

class PropertyChecker(object):

    def __init__(self,dir1,dir2, vision):
        self.abm_release_dir = dir1
        self.model_dir = dir2
        self.abm_release_properties = {}
        self.model_dir_properties = {}
        self.vision = vision
        self.year = int(dir2.split('_')[-1])

        
    def __call__(self):
        self.read_inputs()
        self.add_abm_release_props()
        
        
    def read_inputs(self):
        """ Read property file in the abm release directory and the model directory """
        with open(_join(self.model_dir,'conf','sandag_abm.properties'),'r') as f:
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
    
        with open(_join(self.abm_release_dir,'common','conf','sandag_abm.properties'),'r') as f:
            hold = 1
            props = f.readlines()
            for prop in props:
                prop = prop.rstrip()
                if prop.startswith('#') or len(prop.split('=')) < 2:
                    self.abm_release_properties[hold] = None
                    hold +=1
                else:
                    self.abm_release_properties[prop.split('=')[0].replace(' ','')] = prop.split('=')[1].replace(' ','')
        f.close()
        
        
    def add_abm_release_props(self):
        """ Add any missing properties to the model property file """
        print("Updating Iteration Sample Rates to 1,1,1")
        with open(_join(self.model_dir,'conf','sandag_abm.properties'),'r') as f:
            model_props = f.readlines()
        with open(_join(self.model_dir,'conf','sandag_abm.properties'),'w') as f2:
            for line in model_props:
                if line.startswith("sample_rates"):
                    f2.write("sample_rates = 1.0,1.0,1.0")
                
                elif line.startswith("airport.SAN.mc.uec.file"):
                    if (self.year < 2030) or (self.vision == 'NO'):
                        f2.write("{} = {}\n".format("airport.SAN.mc.uec.file",'AirportModeChoice.SAN2016.xls'))
                    elif self.vision == 'YES' and self.year >= 2030:
                        f2.write("{} = {}\n".format("airport.SAN.mc.uec.file",'AirportModeChoice.SAN2050.xls'))
                else:
                    f2.write(line)

        f.close()
        f2.close()
        missing_props = [prop for prop in self.abm_release_properties.keys() if prop not in self.model_dir_properties.keys() and not self.abm_release_properties[prop] is None]
        for prop in missing_props:
            print("Missing property being added: ",prop)
        with open(_join(self.model_dir,'conf','sandag_abm.properties'),'r') as f:
            model_props = f.readlines()
        for prop in missing_props:
            idx1 = list(self.abm_release_properties.keys()).index(prop)
            idx2 = 0
            i = 0
            while idx2 == 0 and i < 10:
                i +=1
                prev_prop = list(self.abm_release_properties.keys())[idx1 -1]
                if prev_prop in list(self.model_dir_properties.keys()):
                    idx2 = list(self.model_dir_properties.keys()).index(prev_prop)
                else:
                    idx1 -=1
            value = "{} = {}\n".format(prop,self.abm_release_properties[prop])
            if prop == 'airport.SAN.public.transit.connection.mgras':
                if (self.year < 2030) or (self.vision == 'NO'):
                    value = "{} = {}\n".format(prop,'2997')
                elif self.vision == 'YES' and self.year >= 2030:
                    value = "{} = {}\n".format(prop,'2997,3093,2994,3001')
            
            
            model_props.insert(idx2+1,value)
        with open(_join(self.model_dir,'conf','sandag_abm.properties'),'w') as f:
            model_props = "".join(model_props)
            f.write(model_props)
        f.close()


if __name__ == "__main__":
    pc = PropertyChecker(sys.argv[1],sys.argv[2], sys.argv[3])
    pc()        
        
    
