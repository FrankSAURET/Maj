"""Module de traduction centralisé pour Maj."""
import gettext
from typing import Callable

_translator: Callable[[str], str] = gettext.gettext


def setup(localedir: str) -> None:
    """Configure la traduction.

    Utilise la variable d'environnement LANGUAGE (définie par Inkscape)
    pour déterminer la langue. Si aucune traduction n'est trouvée,
    les msgid français du code source sont utilisés tels quels.
    """
    global _translator
    trans = gettext.translation('Maj', localedir=localedir, fallback=True)
    _translator = trans.gettext


def _(message: str) -> str:
    """Traduit un message en utilisant le traducteur configuré."""
    return _translator(message)
