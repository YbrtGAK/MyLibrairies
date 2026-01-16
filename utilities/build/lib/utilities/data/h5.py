# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 11:39:26 2024

@author: yberton
"""

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
                       Gestion des fichiers de données
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
#Convertir en dataframe des fichiers de mesures, tracer des courbes, modifier
#des fichiers de données type h5

"""""""""""""""""""""""""""""""""Fichiers h5"""""""""""""""""""""""""""""""""

#imports
import h5py
import pandas as pd
import numpy as np

def channel_attr_to_dict(channel):
    
    """Get a signal's attributes (channel, ...)"""
    
    #Get and shape channel's attributes
    channel = str(channel.attrs["label"]).replace("{","") #Withdraw "{"
    channel = channel.replace("}","")[1:][1:][:-1].split(',') #withdraw "}"
    channel = [e.split(':') for e in channel] #withdraw ":"
    
    #Get those attributes in a dictionary
    dict1 = {}
    for e in channel : dict1[e[0].split('"')[1]] = e[1].split('"')[1]
    return(dict1)

def get_card_data_into_dataframe(card, time):
    
    """Get all signals' data into a table, referenced with their channel"""
    
    data_columns = [e for e in card] #Get the columns' names
    data = [card[i][()] for i in data_columns] #Get the data in a matrix
    data_f = []
    for array in data :  
        data_f.append([e[0] for e in array])
    #data1 = [array[0] for array in data1]
    Ldict = [channel_attr_to_dict(card[e]) for e in data_columns] #Get dictionaries with channels' number
    Lchannels = [e["data"].split("\'")[1][:-1] for e in Ldict]
    Lchannels = [e.split(" ")[-1] for e in Lchannels]
    
    #Get the channels' number 
    dct = {}
    for i in range(0,len(Lchannels)) : 
        dct[Lchannels[i]] = data[i]
                
    return(pd.DataFrame(np.array(data_f).transpose(), columns = Lchannels, index=time))    

def h5_to_df(h5py_file_path, scan:str=None, detector:str=None,axes:str=None, data:str=None,cards:[str]=None,nidaq_usb=False) :
    
    """Get data from h5py file into a dataframe table"""
    
    if nidaq_usb:
            with h5py.File(h5py_file_path, "r", locking=False) as f:
            # Get time information
                time = [pd.Timestamp(e, unit='s')
                    for e in f['RawData']['Datalogger000']['Detector000']['NavAxes']['Axis00']]

                module = f['RawData']['Datalogger000']['Detector000']['Data0D']['CH00']

                data_columns = list(module.keys())
                data = [module[col][()] for col in data_columns]

                dicti = {}
                for col, values in zip(data_columns, data):
                    dicti[col] = values.flatten()   # <-- IMPORTANT (transforme en 1D)
                df = pd.DataFrame(dicti, index=time)
            return(df)
    else : 
        with h5py.File(h5py_file_path, "r",locking=False) as f:
            
            #Get time information
            time = [pd.Timestamp(e,unit='s', tz='Europe/Paris') for e in f['RawData'][scan][detector][axes]["Axis00"]]

            #Get the card's data
            Lcard = [f['RawData'][scan][detector][data][card] for card in cards]
            
            #Get the cards data into a dataframe
            dfs = [get_card_data_into_dataframe(card,time) for card in Lcard]
        
    return(dfs)

def datx_to_dict(path) :
        # unpack an h5 group into a dict
    def _group2dict(obj):
        return {k: _decode_h5(v) for k, v in zip(obj.keys(), obj.values())}

    # unpack a numpy structured array into a dict
    def _struct2dict(obj):
        names = obj.dtype.names
        return [dict(zip(names, _decode_h5(record))) for record in obj]

    # decode h5py.File object and all of its elements recursively
    def _decode_h5(obj):
        # group -> dict
        if isinstance(obj, h5py.Group):
            d = _group2dict(obj)
            if len(obj.attrs):
                d['attrs'] = _decode_h5(obj.attrs)
            return d
        # attributes -> dict
        elif isinstance(obj, h5py.AttributeManager):
            return _group2dict(obj)
        # dataset -> numpy array if not empty
        elif isinstance(obj, h5py.Dataset):
            d = {'attrs': _decode_h5(obj.attrs)}
            try:
                d['vals'] = obj[()]
            except (OSError, TypeError):
                pass
            return d
        # numpy array -> unpack if possible
        elif isinstance(obj, np.ndarray):
            if np.issubdtype(obj.dtype, np.number) and obj.shape == (1,):
                return obj[0]
            elif obj.dtype == 'object':
                return _decode_h5([_decode_h5(o) for o in obj])
            elif np.issubdtype(obj.dtype, np.void):
                return _decode_h5(_struct2dict(obj))
            else:
                return obj
        # dimension converter -> dict
        elif isinstance(obj, np.void):
            return _decode_h5([_decode_h5(o) for o in obj])
        # bytes -> str
        elif isinstance(obj, bytes):
            return obj.decode()
        # collection -> unpack if length is 1
        elif isinstance(obj, list) or isinstance(obj, tuple):
            if len(obj) == 1:
                return obj[0]
            else:
                return obj
        # other stuff
        else:
            return obj

    # open the file and decode it
    with h5py.File(path, 'r') as f:
        h5data = _decode_h5(f)

    return h5data
