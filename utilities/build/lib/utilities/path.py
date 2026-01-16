# -*- coding: utf-8 -*-
"""
Created on Mon Aug  1 10:23:16 2022

@author: YB263935
"""

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
                             Gestion des chemins
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

#Imports
import tkinter as tk
from tkinter import filedialog
import os
from os import walk

# Récupérer, Acquérir des chemins de dossiers et/ou fichiers

def getAFilesPath(window_title = None, filetypes  = [('All files','*.*')]) :
    
    """Renvoie le chemin vers un fichier"""
    
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfile(title = window_title, filetypes=filetypes)
    try:
        return(path.name)
    except AttributeError :
        return(None)

def getFilesPaths(window_title = None, filetypes = None) :
    
    """Renvoie les chemins respectifs de plusieurs fichiers dans une liste"""
    
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilenames(parent = root, filetypes=filetypes,
     title = window_title)
    return(path)

def getADirsPath(window_title = None):
    
    """Renvoie le chemin vers un dossier"""
    
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askdirectory(title = window_title)
    return(path)    

def create_folder(name):
    
    """ create a folder """
    
    if not os.path.exists(name):
        os.makedirs(name)

def getAFilesPathToSave(window_title = None, filetypes  = [('All files','*.*')]) :
    
    """Renvoie un chemin pour un fichier à sauvegarder"""
    
    root = tk.Tk()
    root.withdraw()
    path = filedialog.asksaveasfile(title = window_title, filetypes=filetypes)
    return(path.name)

def files_name_to_list(path : str) -> str :
    
    """ Renvoie une liste contenant les noms des fichiers excels des essais de
    Devenir"""
    
    listeFichiers = [] #Instancie la liste des noms de fichiers
    
    for (files_path, sousRepertoires, fichiers) in walk(path): #Ajoute les noms
        listeFichiers.extend(fichiers)
        
    for i in range(0,len(listeFichiers)) : 
        listeFichiers[i] = path + '/' + listeFichiers[i]
        

    return(listeFichiers) #Retourne la liste des noms et le chemin absolu

def getAllFilesOfAGivenFormat(dirpath:str,fmt:str ) -> str : 
    
    """Renvoie la liste des chemins de tous les fichiers dans un dossier 
    dont le format correspond à celui renseigné par l'utilisateur.ice. """
    
    l = []
    if fmt[0] != '.' : fmt = '.' + fmt
    for dirpath, dirnames, filenames in os.walk(dirpath):
       for filename in filenames:
          if filename.endswith(fmt):
             l.append(dirpath + '/' + filename)
    return(l)
    

