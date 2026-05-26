"""Backward-compatible Pinterest CSV export.

Pinterest's Ads Bulk Editor template requires matching local media files when
the "Media File Name" column is used. For this bot, the safer daily download is
the organic bulk upload CSV that uses public Media URL values instead.
"""

from config import PINTEREST_BULK_CSV
from modules.pinterest_upload_csv import save_pinterest_upload_csv


def save_pinterest_bulk_csv(products: list[dict], path: str = PINTEREST_BULK_CSV) -> str | None:
    return save_pinterest_upload_csv(products, path=path)
