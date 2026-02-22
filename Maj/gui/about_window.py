"""
Fenêtre "À propos" du gestionnaire d’extensions.
Affiche le lien GitHub et le logo Maj.svg.
"""
import tkinter as tk
from tkinter import ttk
import webbrowser

class AboutWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("À propos")
        self.create_widgets()

    def create_widgets(self):
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        try:
            from __init__ import __version__, __author__, __license__
        except Exception:
            __version__ = "?"
            __author__ = "?"
            __license__ = "?"

        self.configure(bg="#e8f5e9")
        # Logo en grand
        try:
            logo = tk.PhotoImage(file="assets/maj.png")
            lbl_logo = tk.Label(self, image=logo, bg="#e8f5e9")
            lbl_logo.image = logo
            lbl_logo.pack(pady=(10, 10))
        except Exception:
            pass
        # Nom et version
        lbl_name = tk.Label(self, text="Gestionnaire d’extensions Inkscape – Maj", font=("Arial", 16, "bold"), bg="#e8f5e9", fg="#145a32")
        lbl_name.pack(pady=(0, 5))
        lbl_version = tk.Label(self, text=f"Version : {__version__}", font=("Arial", 12), bg="#e8f5e9", fg="#145a32")
        lbl_version.pack()
        lbl_author = tk.Label(self, text=f"Auteur : {__author__}", font=("Arial", 12), bg="#e8f5e9", fg="#145a32")
        lbl_author.pack()
        lbl_license = tk.Label(self, text=f"Licence : {__license__}", font=("Arial", 12), bg="#e8f5e9", fg="#145a32")
        lbl_license.pack(pady=(0, 10))
        # Lien GitHub
        link = tk.Label(self, text="Voir le projet sur GitHub", fg="blue", cursor="hand2", bg="#e8f5e9", font=("Arial", 12, "underline"))
        link.pack(pady=(0, 10))
        link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/FrankSAURET/Maj"))
