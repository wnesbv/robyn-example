
from __future__ import annotations

from datetime import datetime

import json, string, secrets, time

from passlib.hash import pbkdf2_sha1

from account.models import User

from db_config.storage_config import Base, engine, async_session


def get_random_string():
    alphabet = string.ascii_letters + string.digits
    prv_key = "".join(secrets.choice(alphabet) for i in range(32))
    return prv_key


async def on_app_startup() -> None:
    async with engine.begin() as conn:
        # ..
        start = time.time()
        print(" start..")
        # ..
        await conn.run_sync(Base.metadata.create_all)
        # ..
        end = time.time()
        print(" end..", end - start)

    async with async_session() as session:
        async with session.begin():
            # ..
            password_hash = pbkdf2_sha1.hash("password")
            # ..
            start = time.time()
            print(" start add_all..")
            # ..
            session.add_all(
                [
                    User(
                        name="one",
                        email="one@example.com",
                        password=password_hash,
                        is_admin=True,
                        is_active=True,
                        privileged=True,
                        email_verified=True,
                        created_at=datetime.now(),
                    ),
                    User(
                        name="two",
                        email="two@example.com",
                        password=password_hash,
                        is_admin=False,
                        is_active=True,
                        privileged=True,
                        email_verified=True,
                        created_at=datetime.now(),
                    ),
                    User(
                        name="three",
                        email="three@example.com",
                        password=password_hash,
                        is_admin=False,
                        is_active=True,
                        email_verified=True,
                        created_at=datetime.now(),
                    ),
                    User(
                        name="four",
                        email="four@example.com",
                        password=password_hash,
                        is_admin=False,
                        is_active=True,
                        email_verified=True,
                        created_at=datetime.now(),
                    ),
                ]
            )
            await session.flush()
        await session.commit()
        end = time.time()
        print(" end add_all..", end - start)
    await engine.dispose()


async def on_app_shutdown() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
