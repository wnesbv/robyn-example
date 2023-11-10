
from pathlib import Path

import os, shutil


from config.settings import BASE_DIR


async def del_user(email):
    # ..
    directory = [
        (BASE_DIR / f"static/upload/{email}"),
    ]
    for i in directory:
        if Path(i).exists():
            shutil.rmtree(i)
