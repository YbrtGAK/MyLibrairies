# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 11:44:44 2024

@author: yberton
"""

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
                       Gestion des fichiers de données
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
#Convertir en dataframe des fichiers de mesures, tracer des courbes, modifier
#des fichiers de données type lvm

#imports
import pandas as pd
from datetime import datetime, timedelta


"""""""""""""""""""""""""""""""""Fichiers lvm"""""""""""""""""""""""""""""""""

def lvm_to_df(lvm_file_path, skiprows=22):
    """Convertit un fichier lvm en dataframe"""
    
    header = pd.read_csv(lvm_file_path, sep='\t', on_bad_lines='skip',
                         decimal=',', encoding='unicode_escape')
    
    raw_date = header.iloc[8,1]
    raw_time = header.iloc[9,1]
    
    # Rebuild time string with optional microseconds
    try:
        t_start = (raw_time.split(':')[0] + ":" + raw_time.split(':')[1] + ":" +
                   raw_time.split(':')[2].split(',')[0] + '.' +
                   ''.join([raw_time.split(':')[2].split(',')[1][i] for i in range(5)]))
    except IndexError:
        # if no microseconds → just keep HH:MM:SS
        t_start = raw_time.split(',')[0]
    
    datetime_str = raw_date + " " + t_start
    
    # Try parsing with microseconds, else without
    try:
        d_start = datetime.strptime(datetime_str, "%Y/%m/%d %H:%M:%S.%f")
    except ValueError:
        d_start = datetime.strptime(datetime_str, "%Y/%m/%d %H:%M:%S")
    
    df = pd.read_csv(lvm_file_path, sep='\t', on_bad_lines='skip',
                     skiprows=skiprows, decimal=',', encoding='unicode_escape')
    
    df.index = [d_start + timedelta(seconds=i*10) for i in df.index]
    return df

