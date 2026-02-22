import ssl
ssl._create_default_https_context = ssl._create_unverified_context
"""
Fenêtre principale du gestionnaire d’extensions Inkscape.
Affiche la liste des extensions, permet l’installation, la mise à jour, la suppression.
"""
import tkinter as tk
import os
from tkinter import ttk
from core.repo_manager import RepoManager
from core.installer import Installer
from core.updater import Updater
from core.validator import Validator
from core.config import Config
import sys
import json
import urllib.request
from core.provider_utils import ProviderUtils


class MainWindow(tk.Frame):
    def scan_installed_extensions(self):
        """
        Parcourt le dossier d'extensions utilisateur, lit les Info.json, complète installed_extensions.json,
        et retourne la liste des extensions installées.
        """
        if sys.platform.startswith('win'):
            user_dir = os.path.expandvars(r'%APPDATA%')
            ext_dir = os.path.join(user_dir, 'Inkscape', 'extensions')
        else:
            user_dir = os.path.expanduser('~')
            ext_dir = os.path.join(user_dir, '.config', 'inkscape', 'extensions')
               
        installed_by_repo = {}
        for root, dirs, files in os.walk(ext_dir):
            if 'Info.json' in files:
                info_path = os.path.join(root, 'Info.json')
                try:
                    with open(info_path, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                    # Vérifier le type
                    if info.get('type') == 'InkScape extension':
                        info['Installed_dir'] = root
                        local_name = info.get('name')
                        if local_name:
                            installed_by_repo[local_name] = info
                except Exception as e:
                    self.log(f"Erreur lecture {info_path}: {e}", erreur=True)
        # Tri alphabétique
        sorted_installed = dict(sorted(installed_by_repo.items(), key=lambda x: x[0].lower()))
        # Écriture du fichier installed_extensions.json
        installed_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'installed_extensions.json')
        try:
            with open(installed_path, 'w', encoding='utf-8') as f:
                json.dump(sorted_installed, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"Erreur écriture installed_extensions.json: {e}", erreur=True)
        # Retourne la liste à plat pour compatibilité usages existants
        all_installed = []
        for ext_list in installed_by_repo.values():
            all_installed.extend(ext_list)
        return all_installed

    def get_outdated_extensions(self):
        """
        Compare les versions installées et en ligne, retourne la liste des extensions à mettre à jour.
        """
        import os, json, urllib.request

        installed_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'installed_extensions.json')

        # Charger les extensions installées
        try:
            with open(installed_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, dict):
                extensions = []
                for ext_list in data.values():
                    if isinstance(ext_list, list):
                        extensions.extend(ext_list)
                    elif isinstance(ext_list, dict):
                        extensions.append(ext_list)
            else:
                extensions = data
        except Exception:
            extensions = []

        upgradable = []

        # Parcourir les extensions installées
        for ext in extensions:
            repo_url = ext.get('repos')
            download = ext.get('download')
            local_version = ext.get('version')
            name = ext.get('name')

            online_version = None
            info_json = None

            if repo_url and download:

                # Déterminer le chemin de téléchargement
                if isinstance(download, list):
                    download_path = download[0] if len(download) == 1 else ''
                else:
                    download_path = download if download else ''

                if download_path and not download_path.endswith('/'):
                    download_path += '/'

                # Trouver le provider
                provider = self.provider_utils.get_provider_for_url(repo_url)
                if not provider:
                    continue

                owner, repo = self.provider_utils.split_repo_url(repo_url, provider)

                # Tester toutes les branches possibles
                for branch_try in provider["alternative_main_branch"]:

                    url_Infojson = self.provider_utils.build_file_url(
                        provider,
                        owner,
                        repo,
                        branch_try,
                        download_path + "Info.json"
                    )

                    try:
                        with urllib.request.urlopen(url_Infojson, timeout=5) as response:
                            info_data = response.read().decode('utf-8')
                            info_json = json.loads(info_data)
                            online_version = info_json.get('version')
                            break  # Succès → on arrête
                    except Exception:
                        continue

            # Comparer les versions
            if online_version and local_version:
                def parse_version(v):
                    return [int(x) for x in str(v).split('.') if x.isdigit()]

                try:
                    if parse_version(local_version) < parse_version(online_version):
                        ext_copy = {}
                        if info_json and 'name' in info_json:
                            ext_copy['name'] = info_json['name']
                        ext_copy['online_version'] = online_version
                        ext_copy['local_version'] = local_version
                        upgradable.append(ext_copy)
                except Exception:
                    pass

        return upgradable
    
    def refresh_installable_extensions_list_widget(self):
        import json, os, urllib.request

        # 1. Construire la liste des dépôts (clé = URL du dépôt)
        repos = self.config.repos
        extensions_by_repo = {}

        for repo_url in repos:

            provider = self.provider_utils.get_provider_for_url(repo_url)
            if not provider:
                self.log(f"Provider inconnu pour : {repo_url}", erreur=True)
                continue

            owner, repo = self.provider_utils.split_repo_url(repo_url, provider)

            found = False
            repo_extensions = []

            # Tester toutes les branches possibles
            for branch in provider["alternative_main_branch"]:

                url_json = self.provider_utils.build_file_url(
                    provider,
                    owner,
                    repo,
                    branch,
                    "list_of_inkscape_extensions.json"
                )

                try:
                    with urllib.request.urlopen(url_json, timeout=5) as response:
                        data = response.read().decode("utf-8")
                        ext_list = json.loads(data)

                        ext_items = ext_list['extensions'] if isinstance(ext_list, dict) and 'extensions' in ext_list else []

                        for ext in ext_items:
                            new_ext = {}
                            for key in [
                                "name", "short_description", "subject", "author",
                                "version", "default_install_dir", "compatibility",
                                "repos", "download", "start_here"
                            ]:
                                if key in ext:
                                    new_ext[key] = ext[key]
                            repo_extensions.append(new_ext)

                        found = True
                        break  # Succès → on arrête
                except Exception:
                    continue

            if not found:
                self.log(f"Aucune extension trouvée pour {repo_url}", erreur=True)

            # Tri alphabétique par name
            repo_extensions = sorted(repo_extensions, key=lambda ext: ext.get('name', '').lower())
            extensions_by_repo[repo_url] = repo_extensions

        # 2. Écrire installable_extensions.json
        installable_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'installable_extensions.json')
        try:
            with open(installable_path, 'w', encoding='utf-8') as f:
                json.dump(extensions_by_repo, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"Erreur écriture installable_extensions.json: {e}", erreur=True)

        # 2b. Extraire tous les subjects uniques
        subjects = set()
        for repo_exts in extensions_by_repo.values():
            for ext in repo_exts:
                subj = ext.get('subject')
                if isinstance(subj, list):
                    subjects.update(subj)
                elif subj:
                    subjects.add(subj)

        subjects = sorted(subjects)

        # Sauvegarder dans config.json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            config_data['subjects'] = subjects
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"Erreur écriture subjects dans config.json: {e}", erreur=True)

        # 3. Filtrer selon le sujet sélectionné
        selected_subject = self.subject_var.get() if hasattr(self, 'subject_var') else None
        if selected_subject and selected_subject != "Tous":
            filtered_extensions_by_repo = {}
            for repo, repo_exts in extensions_by_repo.items():
                filtered = []
                for ext in repo_exts:
                    subj = ext.get('subject')
                    if isinstance(subj, list):
                        if selected_subject in subj:
                            filtered.append(ext)
                    elif subj == selected_subject:
                        filtered.append(ext)
                if filtered:
                    filtered_extensions_by_repo[repo] = filtered
            extensions_by_repo = filtered_extensions_by_repo

        # Nettoyer le frame d'affichage
        for widget in self.extension_list_frame.winfo_children():
            widget.destroy()

        from gui.installable_extensions_list_widget import InstallableExtensionsListWidget

        def on_ext_select(ext):
            if ext:
                self.btn_install.config(state=tk.NORMAL)
                self._selected_extension = ext
            else:
                self.btn_install.config(state=tk.DISABLED)
                self._selected_extension = None

        def deselect_extension():
            self.btn_install.config(state=tk.DISABLED)
            self._selected_extension = None

        ext_widget = InstallableExtensionsListWidget(self.extension_list_frame, extensions_by_repo, on_select=on_ext_select)
        ext_widget.pack(fill=tk.BOTH, expand=True)

        deselect_extension()
     
    def __init__(self, master, config: Config):
        super().__init__(master)
        self.master = master
        self.config = config
        # Charger les couleurs depuis config.json (Template[0][colors])
        import json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            template = config_data.get('Template', [{}])[0]
            self.colors = template.get('colors', {})
        except Exception:
            self.colors = {}
        def get_color(key):
            return self.colors.get(key, "#FF00FF")
        self.couleur_fond = get_color('fond_principal')
        self.couleur_fond_bouton_supprimer = get_color('fond_bouton_supprimer')
        self.couleur_fond_saisie = get_color('fond_saisie')
        self.couleur_fond_non_modifiable = get_color('fond_non_modifiable')
        self.couleur_fond_bouton = get_color('fond_bouton')
        self.couleur_onglet = get_color('fond_onglet')
        self.couleur_selectionne = get_color('fond_selectionne')
        self.couleur_focus = get_color('fond_focus')
        self.couleur_texte_sombre = get_color('text_sombre')
        self.couleur_texte_clair = get_color('text_clair')
        self.couleur_lien = get_color('text_lien')
        self.couleur_text_erreur = get_color('text_erreur')
        self.couleur_text_higlight = get_color('text_higlight')
        # Charger format_text si présent
        self.format_text = self.config.format_text if hasattr(self.config, 'format_text') else {}
        self.repo_manager = RepoManager(config)
        self.provider_utils = ProviderUtils(config)
        self.installer = Installer(config)
        self.updater = Updater(config)
        self.validator = Validator()
        # Scan extensions installées et extensions obsolètes dès le lancement
        self.scan_installed_extensions()
        self.get_outdated_extensions()
        self.pack()
        self.create_widgets()

    def center_window(self):
        min_w, min_h = 500, 580
        self.master.minsize(min_w, min_h)
        self.master.update_idletasks()
        w = max(self.master.winfo_width(), min_w)
        h = max(self.master.winfo_height(), min_h)
        ws = self.master.winfo_screenwidth()
        hs = self.master.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.master.geometry(f"{w}x{h}+{x}+{y}")

    def create_widgets(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        self.master.title("Gestionnaire d’extensions Inkscape – Maj")
        try:
            self.master.iconphoto(False, tk.PhotoImage(file="assets/maj.png"))
        except Exception:
            pass
        self.master.configure(bg=self.couleur_fond)
        self.configure(bg=self.couleur_fond)
        style.configure('TCombobox', foreground=self.couleur_texte_sombre, fieldbackground=self.couleur_fond_saisie, background=self.couleur_fond_saisie, selectbackground=self.couleur_fond_bouton, selectforeground=self.couleur_texte_clair)
        style.map('TCombobox',
                fieldbackground=[('readonly', self.couleur_fond_saisie), ('!focus', self.couleur_fond_saisie), ('focus', self.couleur_focus), ('active', self.couleur_fond_saisie), ('selected', self.couleur_fond_bouton)],
                background=[('readonly', self.couleur_fond), ('!focus', self.couleur_fond), ('focus', self.couleur_focus), ('active', self.couleur_fond_saisie), ('selected', self.couleur_fond_bouton)],
                foreground=[('readonly', self.couleur_texte_sombre), ('!focus', self.couleur_texte_sombre), ('focus', self.couleur_texte_clair), ('active', self.couleur_texte_clair), ('selected', self.couleur_texte_clair)],
                selectbackground=[('focus', self.couleur_focus),('selected', self.couleur_focus),('active', self.couleur_focus)],
                selectforeground=[('focus', self.couleur_texte_clair)]
            )
        style.configure('TNotebook.Tab', background=self.couleur_onglet, foreground=self.couleur_texte_clair, font=('Arial', 11, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', self.couleur_selectionne)])
        style.configure('TNotebook', background=self.couleur_fond, borderwidth=0)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        # Onglet extensions installées
        tab_installed = tk.Frame(notebook, bg=self.couleur_fond)
        notebook.add(tab_installed, text="Extensions installées")
        self.create_tab_installed(tab_installed)

        # Onglet ajouter une extension
        tab_add = tk.Frame(notebook, bg=self.couleur_fond)
        notebook.add(tab_add, text="Ajouter une extension")
        self.create_tab_add(tab_add)

        # Zone de log partagée sous le notebook
        lbl_log = tk.Label(self, text="Actions :", bg=self.couleur_fond, fg=self.couleur_texte_sombre, font=("Arial", 11, "bold"))
        lbl_log.pack(anchor="w", padx=10, pady=(0, 0))
        self.text_log = tk.Text(self, height=10, bg=self.couleur_fond_non_modifiable, fg=self.couleur_texte_sombre, font=("Arial", 10))
        self.text_log.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))
        self.text_log.config(state=tk.NORMAL)
        self.text_log.tag_configure("erreur", foreground=self.couleur_text_erreur)
        self.text_log.tag_configure("gras", font=("Arial", 10, "bold"))
        self.text_log.config(state=tk.DISABLED)
        self.text_log.see(tk.END)


        # Déclenche refresh_extension_list_widget à l'entrée dans l'onglet
        def on_tab_changed(event):
            tab_id = notebook.index("current")
            tab_text = notebook.tab(tab_id, "text")
            if tab_text == "Ajouter une extension":
                self.refresh_subject_combobox()
                self.refresh_installable_extensions_list_widget()
        notebook.bind("<<NotebookTabChanged>>", on_tab_changed)

        # Onglet paramètres
        tab_settings = tk.Frame(notebook, bg=self.couleur_fond)
        notebook.add(tab_settings, text="Paramètres")
        self.create_tab_settings(tab_settings)


        # Onglet à propos
        tab_about = tk.Frame(notebook, bg=self.couleur_fond)
        notebook.add(tab_about, text="À propos")
        self.create_tab_about(tab_about)

    def create_tab_installed(self, parent):
        import json, os
        from gui.installed_extensions_list_widget import InstalledExtensionsListWidget
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'config.json')
        # Charger l'état initial de la case à cocher depuis config.json (Params[0])
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            params = config_data.get('Params', [{}])[0]
            show_only_updates = params.get('show_only_updates', False)
        except Exception:
            show_only_updates = False

        self.show_only_updates_var = tk.BooleanVar(value=show_only_updates)

        def save_checkbox_state():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except Exception:
                config_data = {}
            # S'assurer que Params[0] existe
            if 'Params' not in config_data or not isinstance(config_data['Params'], list) or not config_data['Params']:
                config_data['Params'] = [{}]
            config_data['Params'][0]['show_only_updates'] = self.show_only_updates_var.get()
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        # Frame horizontal pour label + case à cocher
        frame_top = tk.Frame(parent, bg=self.couleur_fond)
        frame_top.pack(fill=tk.X, padx=10, pady=(10, 0))
        lbl_extensions = tk.Label(frame_top, text="Extensions installées :", bg=self.couleur_fond, fg=self.couleur_texte_sombre, font=("Arial", 11, "bold"))
        lbl_extensions.pack(side=tk.LEFT)
        chk = tk.Checkbutton(frame_top, text="Uniquement les extensions avec une mise à jour disponible", variable=self.show_only_updates_var, bg=self.couleur_fond, fg=self.couleur_texte_sombre, selectcolor=self.couleur_fond, font=("Arial", 10), command=lambda: refresh_installed_extensions())
        chk.pack(side=tk.LEFT, padx=(15,0))

        # Frame pour la liste
        self.update_list_frame = tk.Frame(parent, bg=self.couleur_fond)
        self.update_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0,5), padx=10)

        def refresh_installed_extensions():
            save_checkbox_state()
            # Nettoyer le frame
            for widget in self.update_list_frame.winfo_children():
                widget.destroy()
            # Charger toutes les extensions installées
            installed_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'installed_extensions.json')
            try:
                with open(installed_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    installed_extensions = []
                    outdated_extensions = self.get_outdated_extensions()
                    for ext_list in data.values():
                        # if isinstance(ext_list, list):
                        #     installed_extensions.extend(ext_list)
                        # elif isinstance(ext_list, dict):
                        if self.show_only_updates_var.get():
                            for outdated in outdated_extensions:
                                if isinstance(outdated, dict) and outdated.get('name') == ext_list.get('name'):
                                    installed_extensions.append(ext_list)
                        else:
                            installed_extensions.append(ext_list)
            except Exception:
                installed_extensions = []
            self.update_list_widget = InstalledExtensionsListWidget(self.update_list_frame, installed_extensions, self.get_outdated_extensions(), on_select=None)
            self.update_list_widget.pack(fill=tk.BOTH, expand=True)

        # Expose la méthode pour pouvoir l'appeler depuis l'extérieur
        self.refresh_installed_extensions = refresh_installed_extensions

        # Appel après la création du widget, pour garantir l'ordre
        self.refresh_installed_extensions()

        frame_btns = tk.Frame(parent, bg=self.couleur_fond)
        frame_btns.pack(fill=tk.X, padx=10, pady=10)
        btn_update = tk.Button(frame_btns, text="Mettre à jour", bg=self.couleur_fond_bouton, fg=self.couleur_texte_clair, command=self.update_selected)
        btn_remove = tk.Button(frame_btns, text="Supprimer", bg=self.couleur_fond_bouton_supprimer, fg=self.couleur_texte_clair, command=self.remove_selected)
        btn_update.pack(side=tk.LEFT, padx=5)
        btn_remove.pack(side=tk.LEFT, padx=5)
        
    def update_selected(self):
        import sys, os, urllib.request, shutil, zipfile, tempfile, json

        # Vérifier qu'une extension est sélectionnée
        ext_widget = getattr(self, 'update_list_widget', None)
        if not ext_widget or not hasattr(ext_widget, 'selected_rows') or not ext_widget.selected_rows:
            self.log("Aucune extension sélectionnée pour mise à jour.", erreur=True)
            return

        # Récupérer l'extension sélectionnée
        ext = None
        for row, ext2, _ in ext_widget.rows:
            if row in ext_widget.selected_rows:
                ext = ext2
                break

        if not ext:
            self.log("Aucune extension sélectionnée pour mise à jour.", erreur=True)
            return

        ext_name = ext.get('name', '?')
        self.log(f"Mise à jour de l'extension : {ext_name}", gras_part=ext_name)

        if 'download' not in ext or not ext['download'] or 'repos' not in ext or not ext.get('Installed_dir'):
            self.log("Information de téléchargement ou dossier d'installation manquante.", erreur=True)
            return

        # Dossier d'installation
        install_dir = ext['Installed_dir']
        os.makedirs(install_dir, exist_ok=True)
        self.log(f"Dossier d'installation : \n   {install_dir}", gras_part=install_dir)

        # Récupération du provider
        repo_url = ext['repos']
        provider = self.provider_utils.get_provider_for_url(repo_url)
        if not provider:
            self.log("Aucun provider compatible trouvé pour ce dépôt.", erreur=True)
            return

        owner, repo = self.provider_utils.split_repo_url(repo_url, provider)

        # Télécharger le ZIP en testant toutes les branches possibles
        tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        branch = None
        zip_url = None

        for branch_try in provider["alternative_main_branch"]:
            try:
                zip_url = self.provider_utils.build_zip_url(provider, owner, repo, branch_try)
                self.log(f"Tentative téléchargement : {zip_url}", gras_part=zip_url)

                with urllib.request.urlopen(zip_url, timeout=15) as response:
                    tmp_zip.write(response.read())

                branch = branch_try
                break  # Succès → on arrête
            except Exception:
                continue

        if branch is None:
            self.log("Impossible de télécharger l'archive du dépôt sur aucune branche connue.", erreur=True)
            return

        tmp_zip.close()

        try:
            # Extraction du ZIP
            temp_extract_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(tmp_zip.name, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)

            # Dossier racine extrait (<repo>-<branch>)
            repo_name = os.path.basename(repo_url)
            root_folder = os.path.join(temp_extract_dir, f"{repo_name}-{branch}")

            # Copier les fichiers/dossiers listés dans 'download'
            for item in ext['download']:
                src_path = os.path.join(root_folder, item)

                if item.endswith('/'):
                    # Dossier
                    src_path = src_path.rstrip('/')
                    dest_path = os.path.join(install_dir, os.path.basename(src_path))

                    if os.path.isdir(src_path):
                        # Sauvegarde éventuelle de Info.json
                        info_json_in_dest = os.path.exists(os.path.join(dest_path, "Info.json"))
                        info_json_in_src = os.path.exists(os.path.join(src_path, "Info.json"))
                        info_json_backup = None

                        if info_json_in_dest and not info_json_in_src:
                            with open(os.path.join(dest_path, "Info.json"), "rb") as f:
                                info_json_backup = f.read()

                        # Vider le dossier cible
                        if os.path.exists(dest_path):
                            for root2, dirs2, files2 in os.walk(dest_path, topdown=False):
                                for name2 in files2:
                                    file_path = os.path.join(root2, name2)
                                    if name2 == "Info.json" and info_json_backup is not None:
                                        continue
                                    try:
                                        os.remove(file_path)
                                    except Exception:
                                        pass
                                for name2 in dirs2:
                                    try:
                                        shutil.rmtree(os.path.join(root2, name2))
                                    except Exception:
                                        pass
                        else:
                            os.makedirs(dest_path, exist_ok=True)

                        # Copier le contenu
                        for item_name in os.listdir(src_path):
                            s = os.path.join(src_path, item_name)
                            d = os.path.join(dest_path, item_name)
                            if os.path.isdir(s):
                                shutil.copytree(s, d, dirs_exist_ok=True)
                            else:
                                shutil.copy2(s, d)

                        # Restaurer Info.json si nécessaire
                        if info_json_backup is not None and not info_json_in_src:
                            with open(os.path.join(dest_path, "Info.json"), "wb") as f:
                                f.write(info_json_backup)

                        self.log(f"Dossier mis à jour : \n   {dest_path}", gras_part=dest_path)

                    else:
                        self.log(f"Dossier non trouvé dans l'archive : {src_path}", erreur=True)

                else:
                    # Fichier
                    if os.path.isfile(src_path):
                        dest_path = os.path.join(install_dir, os.path.basename(src_path))
                        if os.path.exists(dest_path):
                            try:
                                os.remove(dest_path)
                            except Exception:
                                pass
                        shutil.copy2(src_path, dest_path)
                        self.log(f"Fichier mis à jour : \n{dest_path}", gras_part=dest_path)
                    else:
                        self.log(f"Fichier non trouvé dans l'archive : {src_path}", erreur=True)

            # Nettoyage
            shutil.rmtree(temp_extract_dir)
            os.unlink(tmp_zip.name)

            # Message final
            self.text_log.config(state=tk.NORMAL)
            self.text_log.tag_configure("highlight", foreground=self.couleur_text_higlight)
            self.text_log.insert(tk.END, "Mise à jour terminée ! Relancez InkScape pour voir l'extension.\n", "highlight")
            self.text_log.config(state=tk.DISABLED)

            # start_here
            start_here = ext.get('start_here')
            if start_here:
                self.text_log.config(state=tk.NORMAL)
                self.text_log.tag_configure("highlight_gras", foreground=self.couleur_text_higlight, font=("Arial", 10, "bold"))
                self.text_log.insert(tk.END, "   Vous la trouverez ici :\n", "highlight")
                self.text_log.insert(tk.END, start_here + "\n", "highlight_gras")
                self.text_log.config(state=tk.DISABLED)

            self.text_log.see(tk.END)
            self.scan_installed_extensions()
            self.refresh_installed_extensions()

        except Exception as e:
            self.log(f"Erreur lors de la mise à jour : {e}", erreur=True, gras_part=str(e))
            try:
                if os.path.exists(tmp_zip.name):
                    os.unlink(tmp_zip.name)
            except Exception:
                pass

    def remove_selected(self):
        # Suppression de l'extension sélectionnée dans l'onglet extensions installées
        try:
            ext_widget = getattr(self, 'update_list_widget', None)
            if not ext_widget or not hasattr(ext_widget, 'selected_rows') or not ext_widget.selected_rows:
                self.log("Aucune extension sélectionnée pour suppression.", erreur=True)
                return
            # Récupérer l'extension sélectionnée
            ext = None
            for row, ext2, _ in ext_widget.rows:
                if row in ext_widget.selected_rows:
                    ext = ext2
                    break
            if not ext:
                self.log("Aucune extension sélectionnée pour suppression.", erreur=True)
                return
            # Suppression des fichiers de la clé download
            import shutil, os, json
            download = ext.get('download')
            install_dir = ext.get('Installed_dir')
            if download and install_dir:
                files = download if isinstance(download, list) else [download]
                for f in files:
                    # Si c'est un dossier (finissant par /), supprimer le dossier
                    if isinstance(f, str) and f.endswith('/'):
                        try:
                            if os.path.isdir(install_dir):
                                shutil.rmtree(install_dir)
                        except Exception as e:
                            self.log(f"Erreur suppression dossier {install_dir}: {e}", erreur=True)
                    else:
                        path = os.path.join(install_dir, f)
                        try:
                            if os.path.isdir(path):
                                shutil.rmtree(path)
                            elif os.path.isfile(path):
                                os.remove(path)
                        except Exception as e:
                            self.log(f"Erreur suppression {path}: {e}", erreur=True)
            # Supprimer le dossier si vide
            try:
                if install_dir and os.path.isdir(install_dir) and not os.listdir(install_dir):
                    os.rmdir(install_dir)
            except Exception as e:
                self.log(f"Erreur suppression dossier {install_dir}: {e}", erreur=True)
            # Mise à jour du fichier installed_extensions.json
            installed_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'installed_extensions.json')
            try:
                with open(installed_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                name = ext.get('name')
                if isinstance(data, dict):
                    data.pop(name, None)
                elif isinstance(data, list):
                    data = [e for e in data if e.get('name') != name]
                with open(installed_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                self.log(f"Erreur mise à jour installed_extensions.json: {e}", erreur=True)
            # Rafraîchir la liste
            self.refresh_installed_extensions()
            self.log(f"Extension supprimée : {ext.get('name')}")
        except Exception as e:
            self.log(f"Erreur lors de la suppression : {e}", erreur=True)

    def create_tab_add(self, parent):
        # Titres dépôt et sujet
        frame_labels = tk.Frame(parent, bg=self.couleur_fond)
        frame_labels.pack(fill=tk.X, padx=10, pady=(5, 0))
        lbl_repo = tk.Label(frame_labels, text="Choisir un dépôt :", bg=self.couleur_fond, fg=self.couleur_texte_sombre, font=("Arial", 12, "bold"))
        lbl_repo.pack(side=tk.LEFT, padx=(0, 10))
        lbl_subject = tk.Label(frame_labels, text="Sujet :", bg=self.couleur_fond, fg=self.couleur_texte_sombre, font=("Arial", 12, "bold"))
        lbl_subject.pack(side=tk.LEFT, padx=(110, 0), pady=0)

        # Listes déroulantes dépôt et sujet
        frame_selects = tk.Frame(parent, bg=self.couleur_fond)
        frame_selects.pack(fill=tk.X, padx=10, pady=5)
        self.repo_var = tk.StringVar()
        repo_names = ["Tous"] + self.config.repos
        self.repo_combobox = ttk.Combobox(frame_selects, textvariable=self.repo_var, state="readonly", width=40, values=repo_names)
        self.repo_combobox.current(0)
        self.repo_combobox.pack(side=tk.LEFT, padx=(0, 10))
        self.repo_combobox.bind("<<ComboboxSelected>>", lambda e: self.refresh_installable_extensions_list_widget())

        self.subject_var = tk.StringVar()
        self.subject_combobox = ttk.Combobox(frame_selects, textvariable=self.subject_var, state="readonly", width=20)
        self.subject_combobox.pack(side=tk.LEFT, padx=(0, 0))
        self.subject_combobox.bind("<<ComboboxSelected>>", lambda e: self.refresh_installable_extensions_list_widget())
        self.refresh_subject_combobox()

        # Bouton installer
        self.btn_install = tk.Button(frame_selects, text="Installer", bg=self.couleur_fond_bouton, fg=self.couleur_texte_clair, command=self.install_selected, width=12, state=tk.DISABLED)
        self.btn_install.pack(side=tk.LEFT, padx=(10, 0))

        # Liste des extensions installables
        self.extension_list_frame = tk.Frame(parent, bg=self.couleur_fond)
        self.extension_list_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=10)
    
    def install_selected(self):
        import sys, os, urllib.request, shutil, zipfile, tempfile
        ext = getattr(self, '_selected_extension', None)
        ext_name = ext['name']
        self.log(f"Installation de l'extension : {ext_name}", gras_part=ext_name)
        if not ext or 'download' not in ext or not ext['download'] or 'repos' not in ext:
            self.log("Aucune extension sélectionnée ou information de téléchargement manquante.")
            return

        # Déterminer le dossier utilisateur Inkscape
        if sys.platform.startswith('win'):
            user_dir = os.path.expandvars(r'%APPDATA%')
            inkscape_dir = os.path.join(user_dir, 'Inkscape', 'extensions', ext['default_install_dir'])
        else:
            user_dir = os.path.expanduser('~')
            inkscape_dir = os.path.join(user_dir, '.config', 'inkscape', 'extensions', ext['default_install_dir'])

        # Créer le dossier d'installation s'il n'existe pas
        os.makedirs(inkscape_dir, exist_ok=True)
        self.log(f"Dossier d'installation : \n   {inkscape_dir}", gras_part=inkscape_dir)

        # Déterminer la branche à utiliser (main ou master)
        branch = "main"
        repo_url = ext['repos']
        # On tente main puis master si main échoue
        zip_url = repo_url + "/archive/refs/heads/" + branch + ".zip"
        tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        try:
            self.log(f"Téléchargement du dépôt : \n   {zip_url}", gras_part=zip_url)
            try:
                with urllib.request.urlopen(zip_url, timeout=15) as response:
                    tmp_zip.write(response.read())
            except Exception:
                branch = "master"
                zip_url = repo_url + "/archive/refs/heads/" + branch + ".zip"
                self.log(f"Branche 'main' non trouvée, tentative avec 'master' : {zip_url}", gras_part=zip_url)
                with urllib.request.urlopen(zip_url, timeout=15) as response:
                    tmp_zip.write(response.read())
            tmp_zip.close()

            # Extraire le zip dans un dossier temporaire
            temp_extract_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(tmp_zip.name, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)

            # Trouver le dossier racine extrait (nommé <repo>-<branch>)
            repo_name = os.path.basename(repo_url)
            root_folder = os.path.join(temp_extract_dir, f"{repo_name}-{branch}")

            # Copier les fichiers/dossiers listés dans 'download'
            for item in ext['download']:
                src_path = os.path.join(root_folder, item)
                if item.endswith('/'):
                    # Dossier à copier : vider d'abord le dossier cible si présent
                    src_path = src_path.rstrip('/')
                    dest_path = os.path.join(inkscape_dir, os.path.basename(src_path))
                    if os.path.isdir(src_path):
                        # Déterminer si Info.json existe dans le dossier cible et s'il sera remplacé
                        info_json_in_dest = os.path.exists(os.path.join(dest_path, "Info.json"))
                        info_json_in_src = os.path.exists(os.path.join(src_path, "Info.json"))
                        # Sauvegarder Info.json si besoin
                        info_json_backup = None
                        if info_json_in_dest and not info_json_in_src:
                            with open(os.path.join(dest_path, "Info.json"), "rb") as f:
                                info_json_backup = f.read()
                        # Vider le dossier cible (sauf Info.json si besoin)
                        if os.path.exists(dest_path):
                            for root2, dirs2, files2 in os.walk(dest_path, topdown=False):
                                for name2 in files2:
                                    file_path = os.path.join(root2, name2)
                                    if name2 == "Info.json" and info_json_backup is not None:
                                        continue
                                    try:
                                        os.remove(file_path)
                                    except Exception:
                                        pass
                                for name2 in dirs2:
                                    try:
                                        shutil.rmtree(os.path.join(root2, name2))
                                    except Exception:
                                        pass
                        else:
                            os.makedirs(dest_path, exist_ok=True)
                        # Copier le contenu du dossier source dans le dossier cible
                        for item_name in os.listdir(src_path):
                            s = os.path.join(src_path, item_name)
                            d = os.path.join(dest_path, item_name)
                            if os.path.isdir(s):
                                shutil.copytree(s, d, dirs_exist_ok=True)
                            else:
                                shutil.copy2(s, d)
                        # Restaurer Info.json si besoin
                        if info_json_backup is not None and not info_json_in_src:
                            with open(os.path.join(dest_path, "Info.json"), "wb") as f:
                                f.write(info_json_backup)
                        self.log(f"Dossier copié : \n   {dest_path}", gras_part=dest_path)
                    else:
                        self.log(f"Dossier non trouvé dans l'archive : {src_path}", erreur=True)
                else:
                    # Fichier à copier : remplacer uniquement ce fichier
                    if os.path.isfile(src_path):
                        dest_path = os.path.join(inkscape_dir, os.path.basename(src_path))
                        if os.path.exists(dest_path):
                            try:
                                os.remove(dest_path)
                            except Exception:
                                pass
                        shutil.copy2(src_path, dest_path)
                        self.log(f"Fichier copié : \n{dest_path}", gras_part=dest_path)
                    else:
                        self.log(f"Fichier non trouvé dans l'archive : {src_path}", erreur=True)

            # Nettoyer le dossier temporaire
            shutil.rmtree(temp_extract_dir)
            os.unlink(tmp_zip.name)
            # Affiche le message de fin en couleur highlight
            self.text_log.config(state=tk.NORMAL)
            self.text_log.tag_configure("highlight", foreground=self.couleur_text_higlight)
            self.text_log.insert(tk.END, "Installation terminée ! Relancez InkScape pour voir l'extension.\n", "highlight")
            self.text_log.config(state=tk.DISABLED)
            # Log du chemin d'accès dans Inkscape si start_here présent
            start_here = ext.get('start_here')
            if start_here:
                self.text_log.config(state=tk.NORMAL)
                # Tag combiné gras + couleur highlight
                self.text_log.tag_configure("highlight_gras", foreground=self.couleur_text_higlight, font=("Arial", 10, "bold"))
                self.text_log.insert(tk.END, "   Vous la trouverez ici :\n", "highlight")
                self.text_log.insert(tk.END, start_here + "\n", "highlight_gras")
                self.text_log.config(state=tk.DISABLED)
            self.text_log.see(tk.END)
            self.scan_installed_extensions()
            self.refresh_installed_extensions()
        except Exception as e:
            self.log(f"Erreur lors de l'installation : {e}", erreur=True, gras_part=str(e))
            try:
                if os.path.exists(tmp_zip.name):
                    os.unlink(tmp_zip.name)
            except Exception:
                pass

    def refresh_repo_combobox(self):
        repo_names = ["Tous"] + self.config.repos
        self.repo_combobox['values'] = repo_names
        if self.repo_var.get() not in repo_names:
            self.repo_var.set("Tous")
            self.repo_combobox.current(0)
        # Suppression du code utilisant 'parent' non défini

    def create_tab_settings(self, parent):
        parent.configure(bg=self.couleur_fond)

        # Ajouter un dépôt
        frame_repo = tk.Frame(parent, bg=self.couleur_fond)
        frame_repo.pack(fill=tk.X, padx=10, pady=5)
        lbl_add = tk.Label(frame_repo, text="Ajouter un dépôt :", bg=self.couleur_fond, fg=self.couleur_texte_sombre, font=("Arial", 12,"bold"))
        lbl_add.pack(anchor="w", pady=0)
        sub_frame = tk.Frame(frame_repo, bg=self.couleur_fond)
        sub_frame.pack(anchor="w", pady=0)
        self.entry_repo = tk.Entry(sub_frame, width=40)
        self.entry_repo.pack(side=tk.LEFT, padx=5,pady=0)
        btn_add = tk.Button(sub_frame, text="Ajouter", bg=self.couleur_fond_bouton, fg=self.couleur_texte_clair, command=self.add_repo)
        btn_add.pack(side=tk.LEFT, padx=(5,0), pady=0)
        lbl_help = tk.Label(sub_frame, text="Testé uniquement avec un dépot github. Voir l'aide (dans à propos) pour ajouter des dépots.", bg=self.couleur_fond, fg=self.couleur_texte_sombre, font=("Arial", 10), justify=tk.LEFT, width=30, wraplength=200)
        lbl_help.pack(side=tk.LEFT, padx= 0)

        # Liste des dépôts actuels
        lbl_list = tk.Label(parent, text="Dépôts enregistrés :", bg=self.couleur_fond, fg=self.couleur_texte_sombre, font=("Arial", 12, "bold"))
        lbl_list.pack(anchor="w", padx=10, pady=(10, 0))
        frame_list = tk.Frame(parent, bg=self.couleur_fond)
        frame_list.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.listbox_repos = tk.Listbox(frame_list, bg=self.couleur_fond_saisie, fg=self.couleur_texte_sombre, font=("Arial", 11), height=5, selectmode=tk.SINGLE, width=55)
        self.listbox_repos.pack(side=tk.LEFT)
        btn_del_repo = tk.Button(frame_list, text="Supprimer", bg=self.couleur_fond_bouton_supprimer, fg=self.couleur_texte_clair, command=self.delete_repo)
        btn_del_repo.pack(side=tk.LEFT, padx=5)
        self.refresh_repo_listbox()

        # Fréquence de rafraîchissement
        frame_freq = tk.Frame(parent, bg=self.couleur_fond)
        frame_freq.pack(fill=tk.X, padx=20, pady=10)
        lbl_freq = tk.Label(frame_freq, text="Fréquence de vérification des mises à jour (jours) :", bg=self.couleur_fond, fg=self.couleur_texte_sombre, font=("Arial", 12))
        lbl_freq.pack(side=tk.LEFT)
        self.freq_var = tk.IntVar(value=self.config.update_frequency if hasattr(self.config, 'update_frequency') else 7)
        spin_freq = tk.Spinbox(frame_freq, from_=1, to=60, textvariable=self.freq_var, width=5)
        spin_freq.pack(side=tk.LEFT, padx=5)
        def save_frequency():
            freq = self.freq_var.get()
            self.config.update_frequency = freq
            self.config.save()
            self.log(f"Fréquence de vérification enregistrée : {freq} jours")
        btn_save_freq = tk.Button(frame_freq, text="Enregistrer", bg=self.couleur_fond_bouton, fg=self.couleur_texte_clair, command=save_frequency)
        btn_save_freq.pack(side=tk.LEFT, padx=5)

    def refresh_repo_listbox(self):
        self.listbox_repos.delete(0, tk.END)
        for repo in self.config.repos:
            self.listbox_repos.insert(tk.END, repo)

    def add_repo(self):
        repo = self.entry_repo.get().strip()
        if repo and repo not in self.config.repos:
            self.config.repos.append(repo)
            self.config.save()
            self.refresh_repo_listbox()
            self.refresh_repo_combobox()
            self.entry_repo.delete(0, tk.END)
            self.log(f"Dépôt ajouté : {repo}")

    def delete_repo(self):
        sel = self.listbox_repos.curselection()
        if sel:
            repo = self.listbox_repos.get(sel[0])
            if repo in self.config.repos:
                self.config.repos.remove(repo)
                self.config.save()
            self.refresh_repo_listbox()
            self.refresh_repo_combobox()
            self.log(f"Dépôt supprimé : {repo}")

    def save_frequency(self):
        freq = self.freq_var.get()
        self.log(f"Fréquence de vérification enregistrée : {freq} jours")
        # TODO: Sauvegarder dans la config réelle

    def create_tab_about(self, parent):
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        try:
            from __init__ import __version__, __author__, __license__
        except Exception:
            __version__ = "?"
            __author__ = "?"
            __license__ = "?"

        parent.configure(bg=self.couleur_fond)
        # Logo en grand
        try:
            logo = tk.PhotoImage(file="assets/maj.png")
            lbl_logo = tk.Label(parent, image=logo, bg=self.couleur_fond)
            lbl_logo.image = logo
            lbl_logo.pack(pady=(10, 10))
        except Exception:
            pass
        # Nom et version
        lbl_name = tk.Label(parent, text="Gestionnaire d’extensions Inkscape – Maj", font=("Arial", 16, "bold"), bg=self.couleur_fond, fg=self.couleur_texte_sombre)
        lbl_name.pack(pady=(0, 5))
        lbl_version = tk.Label(parent, text=f"Version : {__version__}", font=("Arial", 12), bg=self.couleur_fond, fg=self.couleur_texte_sombre)
        lbl_version.pack()
        lbl_author = tk.Label(parent, text=f"Auteur : {__author__}", font=("Arial", 12), bg=self.couleur_fond, fg=self.couleur_texte_sombre)
        lbl_author.pack()
        lbl_license = tk.Label(parent, text=f"Licence : {__license__}", font=("Arial", 12), bg=self.couleur_fond, fg=self.couleur_texte_sombre)
        lbl_license.pack(pady=(0, 10))
        # Lien GitHub (affiché en bas de l'onglet)
        github_url = "https://github.com/FrankSAURET/Maj"
        lbl_github = tk.Label(parent, text=github_url, font=("Arial", 11, "underline"), fg=self.couleur_lien, bg=self.couleur_fond, cursor="hand2")
        lbl_github.pack(pady=(10, 10))
        lbl_github.bind("<Button-1>", lambda e: os.system(f'start {github_url}'))
    
    def log(self, message, erreur=False, gras_part=None):
        self.text_log.config(state=tk.NORMAL)
        if gras_part and gras_part in message:
            start_idx = self.text_log.index(tk.END)
            before, middle, after = message.partition(gras_part)
            if erreur:
                self.text_log.insert(tk.END, before, "erreur")
                self.text_log.insert(tk.END, middle, ("erreur", "gras"))
                self.text_log.insert(tk.END, after + "\n", "erreur")
            else:
                self.text_log.insert(tk.END, before)
                self.text_log.insert(tk.END, middle, "gras")
                self.text_log.insert(tk.END, after + "\n")
        else:
            if erreur:
                self.text_log.insert(tk.END, message + "\n", "erreur")
            else:
                self.text_log.insert(tk.END, message + "\n")
        self.text_log.see(tk.END)
        self.text_log.config(state=tk.DISABLED)

    def refresh_subject_combobox(self):
        import json, os
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            params = config_data.get('Params', [{}])[0]
            subjects = params.get('subjects', [])
            subjects = sorted(subjects)
        except Exception as e:
            subjects = []
        self.subject_combobox['values'] = ["Tous"] + subjects
        self.subject_combobox.current(0)


