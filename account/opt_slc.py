
import os, jwt, json, string, secrets, functools

from urllib.parse import quote

from robyn import Response

from db_config.settings import settings
from db_config.storage_config import async_session

from options_select.opt_slc import cookies, left_right_first

from .models import User


key = settings.SECRET_KEY
algorithm = settings.JWT_ALGORITHM
EMAIL_TOKEN_EXPIRY_MINUTES = settings.EMAIL_TOKEN_EXPIRY_MINUTES


async def get_token_visited_payload(request):
    if request.headers.get("cookie"):
        token = cookies(request)["visited"]
        if token:
            payload = jwt.decode(token, key, algorithm)
            return payload


async def get_token_visited(request):
    if request.headers.get("cookie"):
        token = cookies(request)["visited"]
        if token:
            payload = jwt.decode(token, key, algorithm)
            email = payload["email"]
            return email


async def get_visited(request, session):
    email = await get_token_visited(request)
    result = await left_right_first(session, User, User.email, email)
    return result


async def get_visited_user(request, session):
    while True:
        user = await get_visited(request, session)
        if not user:
            break
        result = await left_right_first(session, User, User.id, user.id)
        return result


def visited():
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(request, *a, **ka):
            async with async_session() as session:
                user = await get_visited_user(request, session)
                if user:
                    return await func(request, *a, **ka)
                return Response(
                    status_code=302,
                    headers={
                        "location": quote(
                            "/auth/login",
                            safe=":/%#?=@[]!$&'()*+,;",
                        )
                    },
                    description=("Ok..!"),
                )
        return wrapper
    return decorator
