# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 11:46:39 2024

@author: yberton
"""

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
                       Gestion des fichiers de données
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
#Convertir en dataframe des fichiers de mesures, tracer des courbes, modifier
#des fichiers de données type pickel

#imports
import pickle

"""""""""""""""""""""""""""""""Fichiers pickel"""""""""""""""""""""""""""""""""

def save_as_pickle(name_pickle_out, structure_to_store):
    
    """Enregistre un DataFrame en format pickel"""
    
    output = open(name_pickle_out, 'wb')
    pickle.dump(structure_to_store, output)
    output.close()
    
def read_pickle(input_file):
    
    """Ouvre un pickle en format dataframe"""
    
    dictload = pickle.load(open(input_file, 'rb'))
    return dictload


