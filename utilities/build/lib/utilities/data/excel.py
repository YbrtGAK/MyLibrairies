# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 11:38:12 2024

@author: yberton
"""

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
                       Gestion des fichiers de données
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
#Convertir en dataframe des fichiers de mesures, tracer des courbes, modifier
#des fichiers de données type excel, [...]

"""""""""""""""""""""""""""""""Fichiers Excel"""""""""""""""""""""""""""""""""

from openpyxl import load_workbook
import pandas as pd

def xlsx_to_dataframe(file_path:str, sheet:(int,str,None), header:int, index_col:int) -> pd.DataFrame:
    
    return(pd.read_excel(file_path, sheet_name = sheet, header=header, index_col=index_col))


