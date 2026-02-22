import json
import os

class ProviderUtils:
    def __init__(self, config):
        """
        Charge les providers depuis config.repos_providers
        """
        self.providers = config.repos_providers

    def get_provider_for_url(self, repo_url):
        """
        Trouve le provider correspondant à l'URL du dépôt.
        Exemple : https://github.com/FrankSAURET/extension
        """
        for provider in self.providers:
            base = provider["main_url"].split("{owner}")[0]
            if repo_url.startswith(base):
                return provider
        return None

    def split_repo_url(self, repo_url, provider):
        """
        Extrait owner et repo depuis l'URL du dépôt.
        """
        base = provider["main_url"].split("{owner}")[0]
        rest = repo_url[len(base):].strip("/")
        parts = rest.split("/")
        if len(parts) < 2:
            raise ValueError(f"Impossible d'extraire owner/repo depuis {repo_url}")
        return parts[0], parts[1]

    def build_file_url(self, provider, owner, repo, branch, path):
        """
        Construit l'URL d'un fichier brut.
        """
        return provider["download_file_url"].format(
            owner=owner,
            repo=repo,
            branch=branch,
            path=path
        )

    def build_zip_url(self, provider, owner, repo, branch):
        """
        Construit l'URL ZIP du dossier racine.
        """
        return provider["download_folder_url"].format(
            owner=owner,
            repo=repo,
            branch=branch
        )
