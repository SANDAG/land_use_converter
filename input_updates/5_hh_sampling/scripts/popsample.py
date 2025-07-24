"""Script to generate population sample rate by mgra"""
   
   
import pandas as pd
import os
import numpy as np
import sys
import geopandas as gpd
import ast
import warnings
import folium
from folium import FeatureGroup, LayerControl, Map, Marker
from folium.features import DivIcon
import branca.colormap as cm
from branca.colormap import linear
_join = os.path.join

warnings.filterwarnings("ignore")  

class PopSampler(object):

    def __init__(self, params):
        self.params = params
        self.properties = {}
        self.project = []
        self.wdir = ''
        self.mdldir = ''
        self.ludir = ''
        self.run_popsim = ''
        self.override_file = ''
        self.buffer = 0
        self.oversample = 0
        self.undersample = 0
        self.mgra_lu = pd.DataFrame()
        self.mgra_sample_rate = pd.DataFrame()
        self.households = pd.DataFrame()
        self.persons = pd.DataFrame()
        self.households_nb = pd.DataFrame()
        self.persons_nb = pd.DataFrame()
        self.maz_file = None
        self.has_lu = True
        if os.path.isfile(_join(self.wdir,'..','2_landuse_converter','outputs','temp','no_lu.txt')):
            self.has_lu = False
        
    def __call__(self):
        self.read_params()
        if self.has_lu:
            self.assign_sample()
            self.runPopSampler(self.mgra_sample_rate,self.households, self.persons)
            self.runPopSampler(self.mgra_sample_rate,self.households_nb, self.persons_nb, build = False)
            self.create_samplerate_map()
            self.create_qaqc_summary()
        else:
            self.no_lu_sample()

    def add_categorical_legend(self, folium_map, title, colors, labels):
        if len(colors) != len(labels):
            raise ValueError("colors and labels must have the same length.")

        color_by_label = dict(zip(labels, colors))
        
        legend_categories = ""     
        for label, color in color_by_label.items():
            legend_categories += f"<li><span style='background:{color}'></span>{label}</li>"
            
        legend_html = f"""
        <div id='maplegend' class='maplegend'>
          <div class='legend-title'>{title}</div>
          <div class='legend-scale'>
            <ul class='legend-labels'>
            {legend_categories}
            </ul>
          </div>
        </div>
        """
        script = f"""
            <script type="text/javascript">
            var oneTimeExecution = (function() {{
                        var executed = false;
                        return function() {{
                            if (!executed) {{
                                 var checkExist = setInterval(function() {{
                                           if ((document.getElementsByClassName('leaflet-top leaflet-right').length) || (!executed)) {{
                                              document.getElementsByClassName('leaflet-top leaflet-right')[0].style.display = "flex"
                                              document.getElementsByClassName('leaflet-top leaflet-right')[0].style.flexDirection = "column"
                                              document.getElementsByClassName('leaflet-top leaflet-right')[0].innerHTML += `{legend_html}`;
                                              clearInterval(checkExist);
                                              executed = true;
                                           }}
                                        }}, 100);
                            }}
                        }};
                    }})();
            oneTimeExecution()
            </script>
          """
       

        css = """

        <style type='text/css'>
          .maplegend {
            z-index:9999;
            float:right;
            background-color: rgba(255, 255, 255, 1);
            border-radius: 5px;
            border: 2px solid #bbb;
            padding: 10px;
            font-size:12px;
            positon: relative;
          }
          .maplegend .legend-title {
            text-align: left;
            margin-bottom: 5px;
            font-weight: bold;
            font-size: 90%;
            }
          .maplegend .legend-scale ul {
            margin: 0;
            margin-bottom: 5px;
            padding: 0;
            float: left;
            list-style: none;
            }
          .maplegend .legend-scale ul li {
            font-size: 80%;
            list-style: none;
            margin-left: 0;
            line-height: 18px;
            margin-bottom: 2px;
            }
          .maplegend ul.legend-labels li span {
            display: block;
            float: left;
            height: 16px;
            width: 30px;
            margin-right: 5px;
            margin-left: 0;
            border: 0px solid #ccc;
            }
          .maplegend .legend-source {
            font-size: 80%;
            color: #777;
            clear: both;
            }
          .maplegend a {
            color: #777;
            }
        </style>
        """

        folium_map.get_root().header.add_child(folium.Element(script + css))

        return folium_map
       
    def read_params(self):
        #read parameters from parameters file
        self.parameters  =      pd.read_csv(self.params)
        self.wdir        =      self.parameters[self.parameters.Key == 'WORKING_DIR']['Value '].item().strip(' ')
        self.mdldir      =      self.parameters[self.parameters.Key == 'MODEL_DIR']['Value '].item().strip(' ')
        self.ludir       =      self.parameters[self.parameters.Key == 'LU_DIR']['Value '].item().strip(' ')
        self.run_popsim  =      self.parameters[self.parameters.Key == 'RUN_POPSIM']['Value '].item().strip(' ')
        self.override_file  =      self.parameters[self.parameters.Key == 'OVERRIDE_FILE']['Value '].item().strip(' ')
        self.buffer1     =      float(self.parameters[self.parameters.Key == 'BUFFER1']['Value '].item().strip(' '))
        self.buffer2     =      float(self.parameters[self.parameters.Key == 'BUFFER2']['Value '].item().strip(' '))
        self.sample1     =      float(self.parameters[self.parameters.Key == 'SAMPLE1']['Value '].item().strip(' '))
        self.sample2     =      float(self.parameters[self.parameters.Key == 'SAMPLE2']['Value '].item().strip(' '))
        self.sample3     =      float(self.parameters[self.parameters.Key == 'SAMPLE3']['Value '].item().strip(' '))
        #read properties as dictionary
        with open(_join(self.mdldir,'conf','sandag_abm.properties'),'r') as f:
            props = f.readlines()
            for prop in props:
                prop = prop.rstrip()
                if prop.startswith('#') or len(prop.split('=')) < 2:
                    continue
                else:
                    self.properties[prop.split('=')[0].replace(' ','')] = prop.split('=')[1].replace(' ','')
        #read mgra file
        self.mgra_lu = pd.read_csv(_join(self.mdldir, self.properties['mgra.socec.file']))
        if self.run_popsim == 'YES':
            if os.path.isfile(_join(self.wdir,'..','2_landuse_converter','outputs','temp','negative_pop.txt')):
                print("USING TRUNCATED OUTPUTS")
                self.persons    = pd.read_csv(_join(self.wdir,'..','4_final_lu_updates','outputs',self.properties['PopulationSynthesizer.InputToCTRAMP.PersonFile'].split(r'/')[1]))
                self.households = pd.read_csv(_join(self.wdir,'..','4_final_lu_updates','outputs',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile'].split(r'/')[1]))
                self.persons_nb    = pd.read_csv(_join(self.mdldir,'input','original',self.properties['PopulationSynthesizer.InputToCTRAMP.PersonFile']))
                self.households_nb = pd.read_csv(_join(self.mdldir,'input','original',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile']))
            else:
                print("USING POPSIM OUTPUTS")
                self.persons    = pd.read_csv(_join(self.wdir,'..','3_synthetic_population','setup','output','combined',self.properties['PopulationSynthesizer.InputToCTRAMP.PersonFile'].split('/')[1]))
                self.households = pd.read_csv(_join(self.wdir,'..','3_synthetic_population','setup','output','combined',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile'].split('/')[1]))#.drop('SampleRate',axis = 1)
                self.persons_nb    = pd.read_csv(_join(self.mdldir,'input','original',self.properties['PopulationSynthesizer.InputToCTRAMP.PersonFile']))
                self.households_nb = pd.read_csv(_join(self.mdldir,'input','original',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile']))
        elif os.path.isfile(_join(self.wdir,'..','2_landuse_converter','outputs','temp','negative_pop.txt')):
            print("USING TRUNCATED OUTPUTS")
            self.persons    = pd.read_csv(_join(self.wdir,'..','4_final_lu_updates','outputs',self.properties['PopulationSynthesizer.InputToCTRAMP.PersonFile'].split(r'/')[1]))
            self.households = pd.read_csv(_join(self.wdir,'..','4_final_lu_updates','outputs',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile'].split(r'/')[1]))
            self.persons_nb    = pd.read_csv(_join(self.mdldir,'input','original',self.properties['PopulationSynthesizer.InputToCTRAMP.PersonFile']))
            self.households_nb = pd.read_csv(_join(self.mdldir,'input','original',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile']))
        else:
            print("USING ORIGINAL HOUSEHOLDS")
            self.persons    = pd.read_csv(_join(self.mdldir,'input','original',self.properties['PopulationSynthesizer.InputToCTRAMP.PersonFile']))
            self.households = pd.read_csv(_join(self.mdldir,'input','original',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile']))
            self.persons_nb    = pd.read_csv(_join(self.mdldir,'input','original',self.properties['PopulationSynthesizer.InputToCTRAMP.PersonFile']))
            self.households_nb = pd.read_csv(_join(self.mdldir,'input','original',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile']))
        if 'SampleRate' in self.households.columns:
            del self.households['SampleRate']
        if 'SampleRate' in self.households_nb.columns:
            del self.households_nb['SampleRate']
            
        if 'SampleRate' in self.persons.columns:
            del self.persons['SampleRate']
        if 'SampleRate' in self.persons_nb.columns:
            del self.persons_nb['SampleRate']
                    
            
    def assign_sample(self):
        """ read project mgra and find mgra's within buffer distance of them"""

        self.project  = pd.read_excel(self.override_file, sheet_name = 'Project_Data').dropna(subset = ['MGRA'])
        self.project  = self.project.MGRA.unique()
        self.maz_file = gpd.read_file(_join(self.ludir,'inputs','SANDAG_MGRA_final.shp'))
        self.maz_file = self.maz_file.to_crs({'init':'epsg:2228'})
        self.maz_file['geometry'] = self.maz_file['geometry'].representative_point()
        buffer1 = self.maz_file[self.maz_file.MGRA.isin(self.project)]
        buffer1['geometry'] = buffer1['geometry'].buffer(self.buffer1*5280)
        samples1 = gpd.sjoin(self.maz_file, buffer1.drop('MGRA',axis = 1), how = 'right', op = 'within').MGRA.unique()
        
        buffer2 = self.maz_file[self.maz_file.MGRA.isin(self.project)]
        buffer2['geometry'] = buffer2['geometry'].buffer(self.buffer2*5280)
        samples2 = gpd.sjoin(self.maz_file, buffer2.drop('MGRA',axis = 1), how = 'right', op = 'within').MGRA.unique()
        
        
        self.mgra_sample_rate = self.mgra_lu.copy()
        self.mgra_sample_rate['SampleRate'] = self.sample3
        
        self.mgra_sample_rate.loc[self.mgra_sample_rate['mgra'].isin(samples2),'SampleRate'] = self.sample2
        self.mgra_sample_rate.loc[self.mgra_sample_rate['mgra'].isin(samples1),'SampleRate'] = self.sample1
        self.mgra_sample_rate = self.mgra_sample_rate[['mgra','SampleRate']].rename(columns = {'mgra':'MGRA'})
        self.mgra_sample_rate.to_csv(_join(self.wdir,'outputs','temp','mgra_sample_rate_file.csv'),index = False)
        return
        

   
        
    def sample_hhs(self,group):
        #sample using the mgra sample rate with replacement and a stable group seed
        seed = int(group.taz.min()*100 + group.hhincbin.min()*10 + group.hhsizebin.min())
        sample = group.sample(frac=group.SampleRate.min(), replace=True, random_state=seed)
        if len(sample)==0:
            print( 'mgra ',group.taz.min(),' inc ', group.hhincbin.min(), ' size ', group.hhsizebin.min(),' sample is empty. Sample rate is ',group.SampleRate.min(),' size is ',len(group))
            sample = group
            effectiveRate = 1.0
            hhexpfac = 1.0
        else:
            if group.SampleRate.min()%1 == 0:
                sample = pd.concat([group for i in range(0,int(group.SampleRate.min()))])
                sample['SampleRate'] = group.SampleRate.min()
            else:
                #set hh expansion factor based on actual sample size since sampling is lumpy
                hhexpfac = 1.0 / (len(sample)*1.0/len(group)) 
                sample.hhexpfac = 1.0 / (len(sample)*1.0/len(group)) 
                effectiveRate = 1.0 * len(sample)/len(group)        
                print("mgra %i hhincbin %s hhsizebin %s sample rate %.2f effective rate %.2f" % (group.mgra.min(), group.hhincbin.min(), group.hhsizebin.min(), group.SampleRate.min(), 1.0 / sample.hhexpfac))
        
                # replace the target sample rate with the actual sample rate
                sample['SampleRate'] = effectiveRate
        
        return(sample)


    def runPopSampler(self,tazSampleRateFileName, hhFileName, perFileName, build = True):
        # Read in TAZ sample rate table as pandas dataframe
        sampleRates = tazSampleRateFileName#pd.read_csv(tazSampleRateFileName, delimiter=',')
        
        # Read in pop syn household table as pandas dataframe
        households = hhFileName#pd.read_csv(hhFileName, delimiter=',')
        # Read in popsyn persons table as pandas dataframe
        persons = perFileName#pd.read_csv(perFileName, delimiter=',')
        print(persons.columns)
        #join sample rate by home taz
        if 'SampleRate' in households.columns:
            del households['SampleRate']
        households = pd.merge(households, sampleRates, left_on = 'mgra', right_on='MGRA')
        for col in households.columns:
            print("sampling",col)
        #bin hhs by income and size
        incbins = [-99999, 50000, 100000, households['hinc'].max()+1]
        households['hhincbin'] = pd.cut(households['hinc'], incbins, labels=False) # Double check household income field
        sizebins = [-1, 1, 2, 3, households['persons'].max()+1]
        households['hhsizebin'] = pd.cut(households['persons'], sizebins, labels=False) # Double check househod size field
        #group hhs by taz, hhincbin, hhsizebin and sample and reset index
        hhsGrouped = households.groupby(["mgra","hhincbin","hhsizebin"],as_index = False)
        new_households = hhsGrouped.apply(self.sample_hhs)
        # new_households = new_households.reset_index(drop=True)
        #update ids and expand persons
        new_households['hhno_new'] = range(1,len(new_households)+1)
        new_persons = pd.merge(persons, new_households[["hhid","hhno_new", "SampleRate"]], left_on="hhid", right_on="hhid", )
        print(new_persons.columns)
        new_households['hhid'] = new_households['hhno_new'].astype(np.int32)
        new_persons['hhid'] = new_persons['hhno_new'].astype(np.int32)
        
        #new_persons = pd.merge(new_persons, sampleRates, left_on='mgra', right_on='MGRA')

        #delete added fields
        del new_households['hhno_new']
        del new_households['MGRA']
    #    del new_households['SampleRate']
        del new_households['hhincbin']
        del new_households['hhsizebin']
        del new_persons['hhno_new']
        #del new_persons['MGRA']
        #del new_persons['mgra']
        
        #sort data
        new_households.sort_values('hhid', ascending=True, inplace=True)
        new_persons.sort_values(['hhid','pnum'], ascending=[True,True], inplace=True)
        
        #reset perid to sequential number
        new_persons['perid'] = range(1,len(new_persons)+1)

        # Write new households file to output data folder
        # new_households.to_csv('new_'+hhFileName, sep=',', index=False)
        # Write new persons file to output data folder
        # new_persons.to_csv('new_'+perFileName, sep=',', index=False)
        if build:
            new_households.to_csv(_join(self.wdir,'outputs','build',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile'].split('/')[1]), index = False)
            new_persons.to_csv(_join(self.wdir,'outputs','build',self.properties['PopulationSynthesizer.InputToCTRAMP.PersonFile'].split('/')[1]),index = False)
        else:
            new_households.to_csv(_join(self.wdir,'outputs','no_build',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile'].split('/')[1]), index = False)
            new_persons.to_csv(_join(self.wdir,'outputs','no_build',self.properties['PopulationSynthesizer.InputToCTRAMP.PersonFile'].split('/')[1]),index = False)
        # new_households.to_csv(_join(self.mdldir,'..','Build',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile']),index = False)
        # new_persons.to_csv(_join(self.mdldir,'..','Build',self.properties['PopulationSynthesizer.InputToCTRAMP.PersonFile']),index = False)
    
    def no_lu_sample(self):
        self.households_nb['SampleRate'] = 1
        self.persons_nb['SampleRate'] = 1
        self.households_nb.to_csv(_join(self.wdir,'outputs','build',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile'].split('/')[1]), index = False)
        self.persons_nb.to_csv(_join(self.wdir,'outputs','build',self.properties['PopulationSynthesizer.InputToCTRAMP.PersonFile'].split('/')[1]),index = False)
        self.households_nb.to_csv(_join(self.wdir,'outputs','no_build',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile'].split('/')[1]), index = False)
        self.persons_nb.to_csv(_join(self.wdir,'outputs','no_build',self.properties['PopulationSynthesizer.InputToCTRAMP.PersonFile'].split('/')[1]),index = False)
        
    def create_samplerate_map(self):
        if len(self.project) <= 0:
            print("error, no project")
            sys.exit()
        print("create_samplerate_map")
        mgra_file = gpd.read_file(os.path.join(self.ludir, 'inputs', 'SANDAG_MGRA_final.shp'))
        mgra_file = mgra_file.to_crs({'init':'epsg:4326'})
        print("read mgra")
        final_sample_rates = pd.read_csv(_join(self.wdir,'outputs','build',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile'].split('/')[1]),usecols = ['mgra','taz','SampleRate'])
        final_sample_rates = final_sample_rates.drop_duplicates()
        print("read final sample rates")
        # mgra_file = mgra_file.merge(self.mgra_lu[['mgra','taz']].rename(columns = {'mgra':'MGRA'}), how = 'left', on = 'MGRA')
        mgra_file = mgra_file.merge(final_sample_rates.rename(columns = {'mgra':'MGRA'}), how = 'left', on = 'MGRA')
        print("merged sample rates")
        mgra_file['X'] = mgra_file.geometry.representative_point().x
        mgra_file['Y'] = mgra_file.geometry.representative_point().y
        print("calculated midpoints")

        mgra_file = mgra_file.fillna(-1)
        colormap = linear.YlGn_06.scale(
            mgra_file.SampleRate.min(),
            mgra_file.SampleRate.max())
        colormap.caption = "Sample Rate"
        mgra_file['Color'] = mgra_file['SampleRate'].map(lambda x: colormap(x))
        print("assigned colors")
        style_function = lambda x: {"weight":0.5, 
                                    'color':None,
                                    'fillColor':colormap(x['properties']['SampleRate']), 
                                    'fillOpacity':0.75}
        highlight_function = lambda x: {'fillColor': '#000000', 
                                        'color':'#000000', 
                                        'fillOpacity': 0.50, 
                                        'weight': 0.1}

        sample_map        = folium.Map(location=[mgra_file['Y'].mean(), mgra_file['X'].mean()], zoom_start = 10, tiles = 'cartodbpositron')
        maz_df = mgra_file[mgra_file.SampleRate > 0].dissolve(by = 'SampleRate',as_index = False)

        sample_taz=folium.features.GeoJson(
                maz_df,
                style_function=style_function,
                control=False,
                highlight_function=highlight_function,
                tooltip=folium.features.GeoJsonTooltip(fields=['SampleRate'],
                    aliases=['SampleRate'],
                    sticky=True
                )
            )
        sample_map.add_child(sample_taz)
        sample_map.add_child(colormap)
        group = FeatureGroup(name = "Project", show = True)
        folium.GeoJson(mgra_file[mgra_file.MGRA.isin(self.project)],
            style_function=lambda feature: {
            'fillColor': '#f68b1f',
            'color':'#f68b1f',
            'weight': 0.5,
            'fillOpacity':1}).add_to(group)
        group.add_to(sample_map)
        folium.LayerControl(collapsed = False).add_to(sample_map)
        sample_map.save(_join(self.wdir,'outputs','sample_rate_map.html'))
        
    def create_qaqc_summary(self):
        hh_nb = self.households_nb.copy()
        hh_build = self.households.copy()
        hh_sample_nb = pd.read_csv(_join(self.wdir,'outputs','no_build',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile'].split('/')[1]))
        hh_sample_build = pd.read_csv(_join(self.wdir,'outputs','build',self.properties['PopulationSynthesizer.InputToCTRAMP.HouseholdFile'].split('/')[1]))
        sample_1 = self.mgra_sample_rate[self.mgra_sample_rate.SampleRate == self.sample1].MGRA.unique()
        sample_2 = self.mgra_sample_rate[self.mgra_sample_rate.SampleRate == self.sample2].MGRA.unique()
        sample_3 = self.mgra_sample_rate[self.mgra_sample_rate.SampleRate == self.sample3].MGRA.unique()
        qaqc = pd.DataFrame()
        qaqc['Regional No Build'] = pd.Series([len(hh_nb),len(hh_sample_nb),(1/hh_sample_nb.SampleRate).sum()])
        qaqc['Regional Build'] = pd.Series([len(hh_build),len(hh_sample_build),(1/hh_sample_build.SampleRate).sum()])
        qaqc['Project No Build'] = pd.Series([len(hh_nb[hh_nb.mgra.isin(self.project)]),len(hh_sample_nb[hh_sample_nb.mgra.isin(self.project)]),(1/hh_sample_nb[hh_sample_nb.mgra.isin(self.project)].SampleRate).sum()])
        qaqc['Project Build'] = pd.Series([len(hh_build[hh_build.mgra.isin(self.project)]),len(hh_sample_build[hh_sample_build.mgra.isin(self.project)]),(1/hh_sample_build[hh_sample_build.mgra.isin(self.project)].SampleRate).sum()])
        qaqc['Sample 1 No Build'] = pd.Series([len(hh_nb[hh_nb.mgra.isin(sample_1)]),len(hh_sample_nb[hh_sample_nb.mgra.isin(sample_1)]),(1/hh_sample_nb[hh_sample_nb.mgra.isin(sample_1)].SampleRate).sum()])
        qaqc['Sample 1 Build'] = pd.Series([len(hh_build[hh_build.mgra.isin(sample_1)]),len(hh_sample_build[hh_sample_build.mgra.isin(sample_1)]),(1/hh_sample_build[hh_sample_build.mgra.isin(sample_1)].SampleRate).sum()])
        qaqc['Sample 2 No Build'] = pd.Series([len(hh_nb[hh_nb.mgra.isin(sample_2)]),len(hh_sample_nb[hh_sample_nb.mgra.isin(sample_2)]),(1/hh_sample_nb[hh_sample_nb.mgra.isin(sample_2)].SampleRate).sum()])
        qaqc['Sample 2 Build'] = pd.Series([len(hh_build[hh_build.mgra.isin(sample_2)]),len(hh_sample_build[hh_sample_build.mgra.isin(sample_2)]),(1/hh_sample_build[hh_sample_build.mgra.isin(sample_2)].SampleRate).sum()])
        qaqc['Sample 3 No Build'] = pd.Series([len(hh_nb[hh_nb.mgra.isin(sample_3)]),len(hh_sample_nb[hh_sample_nb.mgra.isin(sample_3)]),(1/hh_sample_nb[hh_sample_nb.mgra.isin(sample_3)].SampleRate).sum()])
        qaqc['Sample 3 Build'] = pd.Series([len(hh_build[hh_build.mgra.isin(sample_3)]),len(hh_sample_build[hh_sample_build.mgra.isin(sample_3)]),(1/hh_sample_build[hh_sample_build.mgra.isin(sample_3)].SampleRate).sum()])
        qaqc['Metric'] = pd.Series(['Original Households','Sampled Households # Records','Sampled Households # Households'])
        qaqc.set_index('Metric').to_csv(_join(self.wdir,'outputs','sampled_households_check.csv'))
        
        
if __name__ == "__main__":
    rf = PopSampler(sys.argv[1])
    rf()