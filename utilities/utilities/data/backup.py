# -*- coding: utf-8 -*-
"""
Created on Wed Apr  9 2026

@author: yberton
"""

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
                    Sauvegarde de fichiers lvm
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
# Copie des fichiers .lvm depuis un ou plusieurs dossiers sources vers un
# périphérique de stockage externe, en conservant l'arborescence des dossiers.

# Imports
import os
import shutil
import tkinter as tk
from tkinter import filedialog


def _select_multiple_dirs(window_title="Sélectionner les dossiers sources"):
    """Permet à l'utilisateur de sélectionner plusieurs dossiers sources
    un par un. La sélection se termine quand l'utilisateur annule le dialogue."""

    dirs = []
    root = tk.Tk()
    root.withdraw()

    while True:
        title = f"{window_title} ({len(dirs)} sélectionné(s) — Annuler pour terminer)"
        path = filedialog.askdirectory(title=title)
        if not path:
            break
        dirs.append(path)

    root.destroy()
    return dirs


def _find_lvm_files(dirpath):
    """Renvoie la liste des chemins absolus de tous les fichiers .lvm
    contenus dans le dossier (récursivement)."""

    lvm_files = []
    for root, dirnames, filenames in os.walk(dirpath):
        for filename in filenames:
            if filename.lower().endswith('.lvm'):
                lvm_files.append(os.path.join(root, filename))
    return lvm_files


def _is_same_file(src, dst):
    """Vérifie si le fichier destination existe déjà avec la même taille
    et la même date de modification que le fichier source."""

    if not os.path.exists(dst):
        return False
    src_stat = os.stat(src)
    dst_stat = os.stat(dst)
    return (src_stat.st_size == dst_stat.st_size
            and int(src_stat.st_mtime) == int(dst_stat.st_mtime))


def backup_lvm(source_dirs=None, destination=None, skip_existing=True):
    """Sauvegarde tous les fichiers .lvm depuis un ou plusieurs dossiers
    sources vers un dossier de destination, en conservant l'arborescence.

    Parameters
    ----------
    source_dirs : list of str, optional
        Liste des chemins des dossiers sources. Si None, un dialogue
        permettra de les sélectionner.
    destination : str, optional
        Chemin du dossier de destination. Si None, un dialogue permettra
        de le sélectionner.
    skip_existing : bool
        Si True, les fichiers déjà présents à la destination avec la
        même taille et date de modification sont ignorés.

    Returns
    -------
    dict
        Résumé de l'opération avec les clés 'copied', 'skipped', 'errors'.
    """

    # Sélection des dossiers sources
    if source_dirs is None:
        source_dirs = _select_multiple_dirs("Sélectionner les dossiers sources")
    if not source_dirs:
        print("Aucun dossier source sélectionné. Opération annulée.")
        return {'copied': 0, 'skipped': 0, 'errors': 0}

    # Sélection du dossier de destination
    if destination is None:
        root = tk.Tk()
        root.withdraw()
        destination = filedialog.askdirectory(
            title="Sélectionner le dossier de destination (stockage externe)")
        root.destroy()
    if not destination:
        print("Aucun dossier de destination sélectionné. Opération annulée.")
        return {'copied': 0, 'skipped': 0, 'errors': 0}

    copied = 0
    skipped = 0
    errors = 0

    for src_dir in source_dirs:
        src_dir = os.path.normpath(src_dir)
        base_name = os.path.basename(src_dir)
        lvm_files = _find_lvm_files(src_dir)

        print(f"\n--- {base_name} : {len(lvm_files)} fichier(s) .lvm trouvé(s) ---")

        for src_file in lvm_files:
            # Chemin relatif par rapport au dossier source
            rel_path = os.path.relpath(src_file, src_dir)
            dst_file = os.path.join(destination, base_name, rel_path)

            # Vérifier si le fichier existe déjà et est identique
            if skip_existing and _is_same_file(src_file, dst_file):
                skipped += 1
                continue

            # Créer le dossier de destination si nécessaire
            dst_dir = os.path.dirname(dst_file)
            os.makedirs(dst_dir, exist_ok=True)

            # Copier le fichier en conservant les métadonnées
            try:
                shutil.copy2(src_file, dst_file)
                copied += 1
                print(f"  Copié : {rel_path}")
            except Exception as e:
                errors += 1
                print(f"  Erreur : {rel_path} — {e}")

    # Résumé
    print(f"\n{'='*50}")
    print(f"Sauvegarde terminée.")
    print(f"  Fichiers copiés  : {copied}")
    print(f"  Fichiers ignorés : {skipped} (déjà à jour)")
    print(f"  Erreurs          : {errors}")
    print(f"{'='*50}")

    return {'copied': copied, 'skipped': skipped, 'errors': errors}
