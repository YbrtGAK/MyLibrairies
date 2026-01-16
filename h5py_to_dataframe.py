import h5py
import os
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

def h5py_to_dataframe(h5py_file_path, scan:str, detector:str,axes:str, data:str,cards:[str]) :
    
    """Get data from h5py file into a dataframe table"""
    
    with h5py.File(h5py_file_path, "r",locking=False) as f:
        
        #Get time information
        time = [pd.Timestamp(e,unit='s', tz='Europe/Paris') for e in f['RawData'][scan][detector][axes]["Axis00"]]

        #Get the card's data
        Lcard = [f['RawData'][scan][detector][data][card] for card in cards]
        
        #Get the cards data into a dataframe
        dfs = [get_card_data_into_dataframe(card,time) for card in Lcard]
        
    return(dfs)

if __name__ == "__main__" :
    
    path = os.path.normpath(getAFilePath())
    dfs = h5py_to_dataframe(path,'Scan000','Detector000','NavAxes',
                                       'Data0D',('CH00', 'CH01'))
