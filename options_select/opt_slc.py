from pathlib import Path

import os, typing
import random, shutil
import urllib.request
from http import cookies as http_cookies

from sqlalchemy import func, and_
from sqlalchemy.future import select

from robyn.templating import JinjaTemplate

from config.settings import BASE_DIR



templates = JinjaTemplate(BASE_DIR / "templates")


def cookie_parser(cookie_string: str) -> typing.Dict[str, str]:

    cookie_dict: typing.Dict[str, str] = {}
    for chunk in cookie_string.split(";"):
        if "=" in chunk:
            key, val = chunk.split("=", 1)
        else:
            key, val = "", chunk
        key, val = key.strip(), val.strip()
        if key or val:
            cookie_dict[key] = http_cookies._unquote(val)
    return cookie_dict


def cookies(request):

    if request.headers.get("cookie"):
        cookie_header = request.headers.get("cookie")
        if cookie_header:
            obj = cookie_parser(cookie_header)
            return obj
    return False


async def all_total(session, model):
    stmt = await session.execute(select(func.count(model.id)))
    result = stmt.scalars().all()
    return result


async def in_all(session, model):
    stmt = await session.execute(select(model))
    result = stmt.scalars().all()
    return result


async def left_right_first(session, model, left, right):
    stmt = await session.execute(select(model).where(left == right))
    result = stmt.scalars().first()
    return result


async def left_right_all(session, model, left, right):
    stmt = await session.execute(select(model).where(left == right))
    result = stmt.scalars().all()
    return result


async def id_and_owner(session, model, obj, id):
    stmt = await session.execute(
        select(model).where(
            and_(
                model.id == id,
                model.owner == obj,
            )
        )
    )
    result = stmt.scalars().first()
    return result


async def owner_request(session, model, obj):
    stmt = await session.execute(select(model).where(model.owner == obj))
    result = stmt.scalars().all()
    return result
