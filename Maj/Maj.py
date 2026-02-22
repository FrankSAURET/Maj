import ssl
ssl._create_default_https_context = ssl._create_unverified_context
"""
Point d'entrée du gestionnaire d’extensions Inkscape.
Lance l’interface graphique Tkinter et initialise la configuration.
"""
from gui.main_window import MainWindow
from core.config import Config
import tkinter as tk


def main():
    config = Config.load()
    root = tk.Tk()
    min_w, min_h = 600, 580
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws // 2) - (min_w // 2)
    y = (hs // 2) - (min_h // 2)
    root.geometry(f"{min_w}x{min_h}+{x}+{y}")
    root.resizable(False, False)  
    app = MainWindow(root, config)
    root.mainloop()

if __name__ == "__main__":
    main()
