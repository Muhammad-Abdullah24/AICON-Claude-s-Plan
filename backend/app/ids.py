"""API ids <-> the names used in the data files, and display names in both languages.

The API speaks lowercase ids ("super_basmati", "rahim_yar_khan"); data files and the service layer use the
AMIS-derived names ("SuperBasmati", "RahimYarKhan"). This module is the only place that maps between them.
"""

from __future__ import annotations

CROP_TO_DATA = {"wheat": "Wheat", "cotton": "Cotton", "irri": "IRRI", "super_basmati": "SuperBasmati"}
MANDI_TO_DATA = {"bahawalpur": "BahawalPur", "vehari": "Vehari", "rahim_yar_khan": "RahimYarKhan"}
CROP_FROM_DATA = {v: k for k, v in CROP_TO_DATA.items()}
MANDI_FROM_DATA = {v: k for k, v in MANDI_TO_DATA.items()}

CROP_NAMES = {
    "wheat": ("گندم", "Wheat"),
    "cotton": ("کپاس (پھٹی)", "Cotton (seed cotton)"),
    "irri": ("چاول (اری)", "Rice (IRRI)"),
    "super_basmati": ("چاول (سپر باسمتی)", "Rice (Super Basmati)"),
}
MANDI_NAMES = {
    "bahawalpur": ("بہاولپور", "Bahawalpur"),
    "vehari": ("وہاڑی", "Vehari"),
    "rahim_yar_khan": ("رحیم یار خان", "Rahim Yar Khan"),
}
