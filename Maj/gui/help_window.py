"""
Fenêtre d’aide pour la configuration des extensions personnalisées.
"""
import tkinter as tk
from tkinter import ttk

class HelpWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Aide - Extensions personnalisées")
        self.create_widgets()

    def create_widgets(self):
        # TODO: Ajouter le contenu d’aide
        pass
