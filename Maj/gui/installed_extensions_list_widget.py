import tkinter as tk
from tkinter import font
import os
import json

class InstalledExtensionsListWidget(tk.Frame):
    """
    Canvas + Frame scrollable, lignes alternées, sélection,
    molette, et icône upgradable à droite sur la ligne version.
    """

    def __init__(self, parent, installed_extensions, outdated_extensions, on_select=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.installed_extensions = installed_extensions
        self.outdated_extensions = outdated_extensions
        self.on_select = on_select

        # Charger config.json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            template = config_data.get('Template', [{}])[0]
            self.colors = template.get('colors', {})
            self.format_text = template.get('format_text', {})
        except Exception as e:
            print("[Maj] Erreur chargement config.json:", e)
            self.colors = {}
            self.format_text = {}

        def get_color(key):
            return self.colors.get(key)
        self.get_color = get_color

        def get_font(key, fallback):
            val = self.format_text.get(key)
            return tuple(val) if val else fallback
        self.get_font = get_font

        # Canvas + Scrollbar
        self.canvas = tk.Canvas(self,
                                bg=self.get_color('fond_ligne_paire'),
                                highlightthickness=0,
                                bd=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar ttk avec style personnalisé
        from tkinter import ttk
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Custom.Vertical.TScrollbar',
            background=self.get_color('scrollbar_slider'),
            troughcolor=self.get_color('scrollbar_trough'),
            bordercolor=self.get_color('scrollbar_trough'),
            arrowcolor=self.get_color('scrollbar_arrow'),
            lightcolor=self.get_color('scrollbar_trough'),
            darkcolor=self.get_color('scrollbar_trough'),
            relief='flat')
        style.map('Custom.Vertical.TScrollbar',
            background=[('active', self.get_color('scrollbar_slider_hover'))]
        )
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview, style='Custom.Vertical.TScrollbar')
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Frame interne
        self.inner = tk.Frame(self.canvas, bg=self.get_color('fond_ligne_paire'))
        self.inner_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        # Fix largeur/marge
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Molette
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

        # Polices
        self.font_name   = font.Font(self, self.get_font('font_bold', ("Arial", 11, "bold")))
        self.font_author = font.Font(self, self.get_font('font_author', ("Arial", 10, "italic")))
        self.font_desc   = font.Font(self, self.get_font('font_desc', ("Arial", 11)))
        self.font_ver    = font.Font(self, self.get_font('font_litle', ("Arial", 9)))

        self._wrap_width = 400

        self.rows = []          # (row_frame, ext, original_bg)
        self.selected_rows = None

        # Icône upgradable
        self._upgradable_icon = None
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'upgradable2.png')
        if os.path.exists(icon_path):
            self._upgradable_icon = tk.PhotoImage(file=icon_path)

        self._populate()

    # --- géométrie / scroll ------------------------------------------------

    def _on_inner_configure(self, event):
        # scrollregion
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # largeur du frame interne = largeur du canvas
        self.canvas.itemconfig(self.inner_window, width=event.width)
        self._wrap_width = max(100, event.width - 30)
        # mettre à jour les wraplength
        for row, ext, original_bg in self.rows:
            for w in row.winfo_children():
                if hasattr(w, "_is_desc"):
                    w.config(wraplength=self._wrap_width)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # --- contenu -----------------------------------------------------------


    def _populate(self):
        # Ajout du panneau danger et du label d'avertissement en haut de la liste
        warning_frame = tk.Frame(self.inner, bg=self.get_color('fond_warning'))
        warning_frame.pack(fill="x", padx=5, pady=(5, 5), anchor="e")

        # Chargement icône panneau danger
        danger_icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'Danger32.png')
        if os.path.exists(danger_icon_path):
            danger_icon = tk.PhotoImage(file=danger_icon_path)
        else:
            danger_icon = None

        if danger_icon:
            tk.Label(warning_frame, image=danger_icon, bg=self.get_color('fond_warning')).pack(side="left", padx=(5, 20))
            # Conserver la référence pour éviter le garbage collection
            warning_frame.danger_icon = danger_icon

        tk.Label(warning_frame,
             text="Attention : seules les extensions avec un fichier Info.json sont listées !",
             font=self.get_font('font_bold', ("Arial", 11, "bold")),
             fg=self.get_color('text_version'),
             bg=self.get_color('fond_warning'),
             wraplength=350,
             justify="left").pack(side="left")

        for idx, ext in enumerate(self.installed_extensions):
            local_version = ext.get('version', '?')
            online_txt = ""
            upgradable = False

            for outdated in self.outdated_extensions:
                if isinstance(outdated, dict) and outdated.get('name') == ext.get('name'):
                    upgradable = True
                    online_txt = f" | Version en ligne : {outdated.get('online_version')}"
                    break
            else:
                online_txt = " - À jour"

            bg_color = (
                self.get_color('fond_ligne_paire')
                if idx % 2 == 0
                else self.get_color('fond_ligne_impaire')
            )

            row_title = tk.Frame(self.inner, bg=bg_color)
            row_title.pack(fill="x", expand=True)

            row_description = tk.Frame(self.inner, bg=bg_color)
            row_description.pack(fill="x", expand=True)

            row_version = tk.Frame(self.inner, bg=bg_color)
            row_version.pack(fill="x", expand=True)

            self.rows.append((row_title, ext, bg_color))
            self.rows.append((row_description, ext, bg_color))
            self.rows.append((row_version, ext, bg_color))

            # ? Ligne 1
            tk.Label(row_title,
                     text=ext.get('name', '?'),
                     font=self.font_name,
                     bg=bg_color,
                     fg=self.get_color('text_sombre')).pack(side="left")

            tk.Label(row_title,
                     text=" par ",
                     font=self.font_author,
                     bg=bg_color,
                     fg=self.get_color('text_by')).pack(side="left")

            tk.Label(row_title,
                     text=ext.get('author', '?'),
                     font=self.font_author,
                     bg=bg_color,
                     fg=self.get_color('text_author')).pack(side="left")

            # ? Ligne 2
            desc_label = tk.Label(row_description,
                                  text=ext.get("short_description", ""),
                                  font=self.font_desc,
                                  bg=bg_color,
                                  fg=self.get_color('text_desc'),
                                  wraplength=self._wrap_width,
                                  justify="left")
            desc_label._is_desc = True
            desc_label.pack(side="left", anchor="w")

            # ? Ligne 3 : texte à gauche, icône à droite
            left_frame = tk.Frame(row_version, bg=bg_color)
            left_frame.pack(side="left", fill="x", expand=True)

            tk.Label(row_version,
                     text=f"(Version installée: {local_version}{online_txt})",
                     font=self.font_ver,
                     bg=bg_color,
                     fg=self.get_color('text_version')).pack(side="left")

            if upgradable and self._upgradable_icon is not None:
                tk.Label(row_version,
                         image=self._upgradable_icon,
                         bg=bg_color).pack(side="right", padx=5)

            # clic sélection
            for row in (row_title, row_description, row_version):
                row.bind("<Button-1>", lambda e, ext=ext: self._select_ext(ext))
                for w in row.winfo_children():
                    w.bind("<Button-1>", lambda e, ext=ext: self._select_ext(ext))

    # --- sélection ---------------------------------------------------------

    def _select_ext(self, ext):
        if self.selected_rows:
            for row, ext2, original_bg in self.rows:
                if row in self.selected_rows:
                    row.config(bg=original_bg)
                    for w in row.winfo_children():
                        w.config(bg=original_bg)

        rows = [row for row, ext2, original_bg in self.rows if ext2 is ext]
        self.selected_rows = rows

        for row in rows:
            row.config(bg=self.get_color('fond_selected_ext'))
            for w in row.winfo_children():
                w.config(bg=self.get_color('fond_selected_ext'))

        if self.on_select:
            self.on_select(ext)
