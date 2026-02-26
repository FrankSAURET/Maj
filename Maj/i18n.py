"""Module de traduction centralisé pour Maj."""
import gettext
import os
from typing import Callable

_translator: Callable[[str], str] = gettext.gettext
lang_code: str = 'fr'


def setup(localedir: str) -> None:
    """Configure la traduction.

    Utilise la variable d'environnement LANGUAGE (définie par Inkscape)
    pour déterminer la langue. Si aucune traduction n'est trouvée,
    les msgid français du code source sont utilisés tels quels.
    Expose ``lang_code`` pour permettre le chargement de fichiers JSON traduits.
    """
    global _translator, lang_code
    # Déterminer le code langue depuis LANGUAGE (ex: "en", "fr:en")
    env_lang = os.environ.get('LANGUAGE', '')
    if env_lang:
        lang_code = env_lang.split(':')[0].split('_')[0]
    else:
        lang_code = 'fr'
    trans = gettext.translation('Maj', localedir=localedir, fallback=True)
    _translator = trans.gettext


def _(message: str) -> str:
    """Traduit un message en utilisant le traducteur configuré."""
    return _translator(message)
