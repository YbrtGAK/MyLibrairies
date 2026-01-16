# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 11:55:12 2024

@author: yberton
"""

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
                            Gestion des Pdfs
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

#imports
from utilities.path import getAFilesPath, getAFilesPathToSave, getFilesPaths
from pypdf import PdfReader, PdfWriter

#Créer, modifier des pdf

def extractFromPdf():
    
    """Créer un pdf à partir de certaines pages (dont les numéros sont donnés
    par l'utilisateur) d'un autre pdf"""
    
    path_original_pdf = getAFilesPath() #Chemin absolu vers le pdf source
    original_pdf = PdfReader(str(path_original_pdf)) #Obtention fichier pdf
    #number_pages = original_pdf.getNumPages() #Nombre maximal de pages du pdf source
    output_pdf_path = getAFilesPathToSave() #Chemin absolu vers le pdf à enregistrer
    list_pages_to_extract = input('Veuillez renseigner les pages que vous voulez extraire du document original dans un format similaire à l exemple suivant  : 1 2 5 3 \n')
    
    #Création d'une liste des pages désirées de type nombre entiers
    list_pages_to_extract = list_pages_to_extract.split(' ') 
    for i in range(0, len(list_pages_to_extract)) : list_pages_to_extract[i] = int(list_pages_to_extract[i])
    pdf_writer = PdfWriter() #Création d'un fichier pdf de sortie
    
    #Récupération des pages désirées du pdf source dans le pdf de sortie
    for page_num in list_pages_to_extract : pdf_writer.addPage(original_pdf.getPage(page_num))
    
    #Enregistrement du fichier pdf de sortie dans le répertoire désiré
    with open(output_pdf_path,'wb') as out:
            pdf_writer.write(out)
    return()

def mergePdf():
    
    """Créer un pdf à partir de n pdf"""
    
    paths = getFilesPaths("Chemins vers les pdfs à fusionner")
    merge_file = PdfWriter()
    for path in paths:
        merge_file.append(PdfReader(path, 'rb'))
    output_pdf_path = getAFilesPathToSave() #Chemin absolu vers le pdf à enregistrer
    merge_file.write(output_pdf_path)
    return()
