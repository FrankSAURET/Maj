import tkinter as tk
from tkinter import font

class InstallableExtensionsListWidget(tk.Frame):
    """
    Widget custom pour afficher les extensions par dépôt avec mise en forme couleur et gras.
    """
    def __init__(self, parent, extensions_by_repo, on_select=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.extensions_by_repo = extensions_by_repo
        self.on_select = on_select
        # Charger les couleurs depuis config.json
        import os, json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            template = config_data.get('Template', [{}])[0]
            self.colors = template.get('colors', {})
        except Exception as e:
            print("[Maj] Erreur chargement config.json:", e)
            self.colors = {}
        def get_color(key):
            return self.colors.get(key) 
        self.get_color = get_color
        
        # Charger les formats de police depuis config.json
        self.format_text = {}
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            template = config_data.get('Template', [{}])[0]
            self.format_text = template.get('format_text', {})
        except Exception as e:
            print("[Maj] Erreur chargement format_text:", e)
            self.format_text = {}
        def get_font(key, fallback):
            val = self.format_text.get(key)
            return tuple(val) if val else fallback
        self.get_font = get_font

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
        self.text = tk.Text(self, wrap=tk.WORD, bg=self.get_color('fond_ligne_paire'), fg=self.get_color('text_sombre'), font=self.get_font('font_base', ("Arial", 11)), state=tk.NORMAL, height=18, width=70, cursor="arrow")
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # Empêcher l'édition
        def block_edit(event):
            return "break"
        self.text.bind("<Key>", block_edit)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview, style='Custom.Vertical.TScrollbar')
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.configure(yscrollcommand=self.scrollbar.set)
        self.bold_font = font.Font(self.text, self.get_font('font_bold', ("Arial", 11, "bold")))
        self.repo_font = font.Font(self.text, self.get_font('font_repo', ("Arial", 12, "bold")))
        self.author_font = font.Font(self.text, self.get_font('font_author', ("Arial", 10, "italic")))
        self.desc_font = font.Font(self.text, self.get_font('font_desc', ("Arial", 11)))
        self.litle_font = font.Font(self.text, self.get_font('font_litle', ("Arial", 9)))
        self._ext_line_map = {}  # map line number to ext dict
        self._selected_line = None
        self.text.bind("<Button-1>", self._on_click)
        self._populate()

    def _on_click(self, event):
        index = self.text.index(f"@{event.x},{event.y}")
        line = int(float(index))
        # Chercher le tag d'extension sur cette ligne
        tags = self.text.tag_names(f"{line}.0")
        ext_tag = None
        for t in tags:
            if t.startswith("ext_"):
                ext_tag = t
                break
        ext = self._ext_tag_map.get(ext_tag)
        # Si on clique sur une zone sans extension (ligne vide ou nom de repo), ne rien faire (garder la sélection)
        if not ext_tag or not ext:
            return
        self._select_ext_tag(ext_tag)
        if self.on_select:
            self.on_select(ext)

    def _select_ext_tag(self, ext_tag):
        # Désélectionner l'ancienne zone
        if hasattr(self, '_selected_ext_tag') and self._selected_ext_tag:
            old_ranges = self.text.tag_ranges(self._selected_ext_tag)
            for i in range(0, len(old_ranges), 2):
                self.text.tag_remove("selected_ext", old_ranges[i], old_ranges[i+1])
        self._selected_ext_tag = ext_tag
        if ext_tag:
            ranges = self.text.tag_ranges(ext_tag)
            for i in range(0, len(ranges), 2):
                self.text.tag_add("selected_ext", ranges[i], ranges[i+1])

    def _populate(self):
        # Si le widget n'est pas encore affiché, attendre et relancer _populate
        if self.text.winfo_width() <= 1:
            self.after(20, self._populate)
            return
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self._ext_tag_map = {}
        repos = list(self.extensions_by_repo.items())
        for idx_repo, (repo, exts) in enumerate(repos):
            start_idx = self.text.index(tk.END)
            self.text.insert(tk.END, repo + "\n", ("repo_bar",))
            end_idx = self.text.index(tk.END)
            numExt=0
            for idx_ext, ext in enumerate(exts):
                ext_tag = f"ext_{id(ext)}"
                ext_start_idx = self.text.index(tk.END)
                bg_tag = "ligne_paire" if numExt % 2 == 0 else "ligne_impaire"
                self.text.insert(tk.END, f"  {ext.get('name', '?')}", ("bold", ext_tag, bg_tag))
                self.text.insert(tk.END, f" par ", ("text_by", ext_tag, bg_tag))
                self.text.insert(tk.END, ext.get("author", "?") + "\n", ("author", ext_tag, bg_tag))
                # Description
                if ext.get("short_description", ""):
                    self.text.insert(tk.END, f"    {ext.get('short_description', '')}\n", ("desc", ext_tag, bg_tag))
                # Ligne version + compatibilité
                version_str = f"Version : {ext.get('version', '?')}"
                compat = ext.get('compatibility', None)
                if isinstance(compat, list):
                    compat_str = ', '.join(str(c) for c in compat)
                elif compat:
                    compat_str = str(compat)
                else:
                    compat_str = ""
                # Calcul alignement : compat à gauche, version à droite
                self.espace_px = self.litle_font.measure(" ")
                left = f"Pour {compat_str}" if compat_str else ""
                right = version_str
                # Espace pour aligner version à droite
                # spaces = " " * max(2, widget_width - total_len)
                
                spaces=" " * (((self.text.winfo_width()-self.litle_font.measure(left+right))//self.espace_px )-8)
                
                
                self.text.insert(tk.END, f"    {left}", ("compatibility", ext_tag, bg_tag))
                self.text.insert(tk.END, f"{spaces}{right}\n", ("version", ext_tag, bg_tag))
                ext_end_idx = self.text.index(tk.END)
                self.text.tag_add(ext_tag, ext_start_idx, ext_end_idx)
                self.text.tag_add(bg_tag, ext_start_idx, ext_end_idx)
                self._ext_tag_map[ext_tag] = ext
                numExt+=1

            if idx_repo < len(repos) - 1:
                self.text.insert(tk.END, "\n")
        self.text.tag_configure("repo_bar", font=self.repo_font, background=self.get_color('fond_repo_bar'), foreground=self.get_color('text_repo_bar'), spacing1=2, spacing3=2)
        self.text.tag_configure("ligne_impaire",  background=self.get_color('fond_ligne_impaire'))
        self.text.tag_configure("ligne_paire",  background=self.get_color('fond_ligne_paire'))
        self.text.tag_configure("bold", font=self.bold_font)
        self.text.tag_configure("author", font=self.author_font, foreground=self.get_color('text_author'))
        self.text.tag_configure("desc", font=self.desc_font, foreground=self.get_color('text_desc'))
        self.text.tag_configure("version", font=self.litle_font, foreground=self.get_color('text_version'), justify="right")
        self.text.tag_configure("selected_ext", background=self.get_color('fond_selected_ext'))
        self.text.tag_configure("text_by", foreground=self.get_color('text_by'))
        self.text.tag_configure("compatibility",font=self.litle_font, foreground=self.get_color('text_compatibility'))
        self.text.config(state=tk.DISABLED)

   