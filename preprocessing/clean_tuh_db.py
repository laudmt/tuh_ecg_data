#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import matplotlib.dates as mdates
import glob
import json
import os, sys, pdb
import numpy as np 
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns



pd.options.display.max_rows = 1000
pd.options.display.max_columns = 1000

plt.style.use('seaborn')

colors = [[0,0,0], [230/255,159/255,0], [86/255,180/255,233/255], [0,158/255,115/255],
          [213/255,94/255,0], [0,114/255,178/255]]

# WIP: to unit test
# Compute time windows for before, during and after seizure
# \param seizure_data np.array of beginning / end of all seizures of the exam in seconds
# \param before_window time lenght in second of before seizure time window
# \param after_window time lenght in second of after seizure time window
# \param df_index_max pandas dataframe max index
# \return bef_seizures_begs np.array of all before seizure begining dataframe index
# \return seizures_begs np.array of all seizure begining dataframe index
# \return seizures_ends np.array of all seizure ending dataframe index
# \return aft_seizures_ends np.array of all after seizure end dataframe index
def compute_seizure_windows_index(seizure_data, before_window, after_window, basale_window, df_index_max):
    
    seizures_begs = []
    seizures_ends = []
    bef_seizures_begs = []
    aft_seizures_ends = []
    basale_seizure_begs = []
    for line in seizure_data:
        seizure_begin = int(np.round(line[0]/10))
        seizure_end = int(np.round(line[1]/10))
        if seizure_begin == seizure_end:
            seizure_end += 1
        
        seizures_begs.append(seizure_begin)
        seizures_ends.append(seizure_end)
            
        bef_seizures_begs.append(seizure_begin - int(before_window/10))
        aft_seizures_ends.append(seizure_end + int(after_window/10))
        basale_seizure_begs.append(seizure_begin - int(before_window/10) - int(basale_window/10))
    
    # Sanities in the limits for before, after seizure and basale index
    for s in range(0, len(seizure_data)):
        if bef_seizures_begs[s] < 0:
            bef_seizures_begs[s] = 0
        if aft_seizures_ends[s] > df_index_max:
            aft_seizures_ends[s] = df_index_max
        if  basale_seizure_begs[s] < 0:
            basale_seizure_begs[s] = 0

    # Sanities with other seizures and time windows overlaps
    for s in range(1, len(seizure_data)):
        
        if bef_seizures_begs[s] < aft_seizures_ends[s-1]:
            bef_seizures_begs[s] = aft_seizures_ends[s-1] + 1
        
        if basale_seizure_begs[s] < aft_seizures_ends[s-1]:
            basale_seizure_begs[s] = aft_seizures_ends[s-1] + 1
        
    return bef_seizures_begs, seizures_begs, seizures_ends, aft_seizures_ends, basale_seizure_begs

def interpolate_invalid_values(array):
    def nan_helper(y):
        return (np.isnan(y) | np.isinf(y)), lambda z: z.nonzero()[0]
    try:
        nans, x= nan_helper(array)
        array[nans]= np.interp(x(nans), x(~nans), array[~nans])
    except:
        print('interpolate_invalid_values : issue with interpolation')
    return array


df = pd.read_csv("Database_links_scores.csv")

# before_window = 180
after_window = 0
basale_window = 180

# Remove exams with missing Feats_filepath (529 NaN Feats_filepath rows)
df = df.dropna(subset=['Feats_filepath'])


for patient in df.Patient_name.unique():
    df_e = df[df.Patient_name == patient]
    list_of_df = []
    idx_seizure_patient = 1
    
    for exam in df_e.Exam_name:
        qrs_data = json.load(open(df_e.loc[df_e.Exam_name  == exam, "RR_intervals_filepath"].values[0], "r"))
        seizure_data = json.load(open(df_e.loc[df_e.Exam_name  == exam, 'Annotations_filepath'].values[0], 'r'))
        data = json.load(open(df_e.loc[df_e.Exam_name  == exam, "Feats_filepath"].values[0], "r"))
        
        # Keep exam if quality score > 0.5 and missing beat < 2
        if (qrs_data["score"]["missing_beats_duration"][1][2] < 2) and (qrs_data["score"]["corrcoefs"][1][2] > 0.8):
            feats = np.array(data["features"])
            t_feats = np.transpose(feats)
            mean_hr = interpolate_invalid_values(t_feats[14])
            date_stamp = pd.to_datetime(t_feats[1], unit='ms', origin=pd.to_datetime(qrs_data['infos']['start_datetime']))
            df_tmp = pd.DataFrame({'date' : date_stamp ,'hr': mean_hr, 'label': t_feats[29], 'patient' : patient, 'exam' : exam})
            
                
            if len(seizure_data['seizure']) == 0:
                for before_window in [120, 180, 240, 300]:
                    df_tmp['window_type_{}'.format(before_window)] = '0'
            else:
                for before_window in [120, 180, 240, 300]:
                    df_tmp['window_type_{}'.format(before_window)] = "{}_{}_s0".format(patient,exam)
                
            for s in range(0, len(seizure_data['seizure'])):
                for before_window in [120, 180, 240, 300]:

                    bef_seizures_begs, seizures_begs, seizures_ends, aft_seizures_ends, basale_seizure_begs = compute_seizure_windows_index(seizure_data['seizure'], before_window, after_window, basale_window, df_tmp.index.max())
        
                    seizure_tag = "{}_{}_{}".format(patient,exam, idx_seizure_patient)
                    
                    beg_bas_s = basale_seizure_begs[s]
                    beg_b_s = bef_seizures_begs[s]
                    beg_s = seizures_begs[s]
                    end_s = seizures_ends[s]
                    end_a_s = aft_seizures_ends[s]
                    
                    if not df_tmp.iloc[beg_s:end_s].empty:
                        # Tag seizure
                        df_tmp.iloc[beg_s:end_s, df_tmp.columns.get_loc('window_type_{}'.format(before_window))] = seizure_tag + "_s"
                        
                        # Tag before seizure
                        if not df_tmp.iloc[beg_b_s:beg_s].empty:
                            df_tmp.iloc[beg_b_s:beg_s, df_tmp.columns.get_loc('window_type_{}'.format(before_window))] = seizure_tag  + "_bs"
        
                        # Tag after seizure
                        if not df_tmp.iloc[end_s:end_a_s].empty:
                            df_tmp.iloc[end_s:end_a_s, df_tmp.columns.get_loc('window_type_{}'.format(before_window))] = seizure_tag  + "_as"
                        
                        # Tag seizure's basale
                        if not df_tmp.iloc[beg_bas_s:beg_b_s].empty:
                            df_tmp.iloc[beg_bas_s:beg_b_s, df_tmp.columns.get_loc('window_type_{}'.format(before_window))] = seizure_tag  + "_basale"
                    
                idx_seizure_patient += 1
                    
            list_of_df.append(df_tmp)
    
    if len(list_of_df) != 0:
        df_patient = pd.concat(list_of_df)
        
        directory = './data/bs_all/'
        if not os.path.exists(directory):
            os.makedirs(directory)
        df_patient.to_csv(directory + '{}_data_file.csv'.format(patient))
