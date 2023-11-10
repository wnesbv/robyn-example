from pathlib import Path, PurePosixPath
from datetime import datetime, timedelta

import io, os, jwt, functools, itertools, json

from multipart import parse_form

from http import cookies

import urllib.parse
from urllib.parse import quote

from passlib.hash import pbkdf2_sha1

from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.future import select

from robyn import Response, SubRouter

from PIL import Image

from mail.verify import verify_mail

from db_config.settings import settings
from db_config.storage_config import async_session

from options_select.opt_slc import templates, in_all, left_right_all, left_right_first

from .token import mail_verify, encode_reset_password, decode_reset_password
from .opt_slc import visited, get_visited_user, get_token_visited_payload
from .models import User
from . import img


key = settings.SECRET_KEY
algorithm = settings.JWT_ALGORITHM
EMAIL_TOKEN_EXPIRY_MINUTES = settings.EMAIL_TOKEN_EXPIRY_MINUTES


auth = SubRouter(__name__, prefix="/auth")


@auth.get("/register")
async def get_register(request):
    template = "/auth/register.html"
    context = {"request": request}
    template = templates.render_template(template, **context)
    return template


@auth.post("/register")
async def user_register(request):
    async with async_session() as session:
        # ..
        obj = dict(urllib.parse.parse_qsl(request.body))
        # ..
        name_exist = await left_right_first(session, User, User.name, obj["name"])
        email_exist = await left_right_first(session, User, User.email, obj["email"])
        # ..
        if name_exist:
            return Response(
                status_code=400,
                headers={"accept": "text/plain"},
                description="name already registered..!",
            )

        if email_exist:
            return Response(
                status_code=400,
                headers={"accept": "text/plain"},
                description="email already registered..!",
            )
        # ..
        new = User()
        new.name = obj["name"]
        new.email = obj["email"]
        new.password = pbkdf2_sha1.hash(obj["password"])
        new.created_at = datetime.now()

        session.add(new)
        await session.commit()
        # ..
        payload = {
            "email": obj["email"],
            "exp": datetime.utcnow()
            + timedelta(minutes=int(EMAIL_TOKEN_EXPIRY_MINUTES)),
            "iat": datetime.utcnow(),
            "scope": "email_verification",
        }
        token = jwt.encode(payload, key, algorithm)
        # ..

        verify = obj["email"]
        await verify_mail(
            f"{request.url.scheme}://{request.url.host}/auth/email-verify?token={token}",
            verify,
        )

        return Response(
            status_code=302,
            headers={
                "location": quote(
                    str("/messages?msg=Go to the specified email address..!"),
                    safe=":/%#?=@[]!$&'()*+,;",
                )
            },
            description=("Ok..!"),
        )


@auth.get("/login")
async def get_login(request):
    context = {"request": request}
    template = templates.render_template(template_name="/auth/login.html", **context)
    print("request_method get", request.method)
    return template


@auth.post("/login")
async def post_login(request):
    # ...
    async with async_session() as session:
        # ..
        obj = dict(urllib.parse.parse_qsl(request.body))
        # ..
        print(" email..", obj["email"])

        user = await left_right_first(session, User, User.email, obj["email"])

        if user:
            if not user.email_verified:
                return Response(
                    status_code=401,
                    headers={"accept": "text/plain"},
                    description="Электронная почта не подтверждена. Проверьте свою почту, чтобы узнать, как пройти верификацию...!",
                )

            if pbkdf2_sha1.verify(obj["password"], user.password):
                # ..
                user.last_login_date = datetime.now()
                # ..
                session.add(user)
                await session.commit()
                # ..
                payload = {
                    "user_id": user.id,
                    "name": user.name,
                    "email": obj["email"],
                }
                token = jwt.encode(payload, key, algorithm)
                # ..

                i = cookies.SimpleCookie()
                i["visited"] = token
                i["visited"]["httponly"] = True
                i["visited"]["path"] = "/"
                i["visited"]["samesite"] = "lax"

                return Response(
                    status_code=302,
                    headers={
                        "Set-Cookie": i.output(header="").strip(),
                        "location": quote(str("/"), safe=":/%#?=@[]!$&'()*+,;"),
                    },
                    description=("Ok..!"),
                )

            return Response(
                status_code=400,
                headers={"accept": "text/plain"},
                description="Invalid (password)..!",
            )
        return Response(
            status_code=400,
            headers={"accept": "text/plain"},
            description="Invalid login (email)..!",
        )


@auth.get("/update-str/:id")
@visited()
# ...
async def get_user_update_str(request):
    # ..
    id = request.path_params["id"]
    user = await get_token_visited_payload(request)
    template = "/auth/update.html"

    async with async_session() as session:
        # ..
        i = await left_right_first(session, User, User.id, user["user_id"])
        # ..
        if user["user_id"] == i.id:
            context = {
                "request": request,
                "i": i,
            }
            return templates.render_template(template, **context)
        return "You are banned - this is not your account..!"


@auth.post("/update-str/:id")
# ...
async def user_update_str(request):
    # ..
    id = request.path_params["id"]
    user = await get_token_visited_payload(request)

    async with async_session() as session:
        # ..
        i = await left_right_first(session, User, User.id, user["user_id"])
        # ..
        if user["user_id"] == i.id:
            # ..
            obj = dict(urllib.parse.parse_qsl(request.body))
            # ..
            query = (
                sqlalchemy_update(User)
                .where(User.id == id)
                .values(
                    name=obj["name"],
                    modified_at=datetime.now(),
                )
                .execution_options(synchronize_session="fetch")
            )
            # ..
            await session.execute(query)
            await session.commit()

            return Response(
                status_code=302,
                headers={
                    "location": quote(
                        f"/auth/details/{id }",
                        safe=":/%#?=@[]!$&'()*+,;",
                    )
                },
                description=("Ok..!"),
            )


@auth.get("/update-img/:id")
@visited()
# ...
async def get_user_update_img(request):
    # ..
    id = request.path_params["id"]
    user = await get_token_visited_payload(request)
    template = "/auth/img.html"

    async with async_session() as session:
        # ..
        i = await left_right_first(session, User, User.id, user["user_id"])
        # ..
        if user["user_id"] == i.id:
            context = {
                "request": request,
                "i": i,
            }
            return templates.render_template(template, **context)
        return "You are banned - this is not your account..!"


@auth.post("/update-img/:id")
# ...
async def user_update_img(request):
    # ..
    id = request.path_params["id"]
    headers = {
        "Content-Type": request.headers.get("content-type"),
        "Content-Length": request.headers.get("content-length"),
    }
    fields = {}
    files = {}
    user = await get_token_visited_payload(request)

    async with async_session() as session:
        # ..
        i = await left_right_first(session, User, User.id, user["user_id"])
        # ..
        if user["user_id"] == i.id:
            if isinstance(request.body, str):
                query = (
                    sqlalchemy_update(User)
                    .where(User.id == id)
                    .values(
                        file=i.file,
                        modified_at=datetime.now(),
                    )
                    .execution_options(synchronize_session="fetch")
                )
                await session.execute(query)
                await session.commit()
                return Response(
                    status_code=302,
                    headers={
                        "location": quote(
                            f"/auth/details/{id }",
                            safe=":/%#?=@[]!$&'()*+,;",
                        )
                    },
                    description=("Ok..!"),
                )

            # ..
            def _on_filed(_field):
                fields[_field.field_name] = _field.value
                print("_field", _field)
            # ...

            name = datetime.now().strftime("%d-%m-%y-%H-%M")
            save_path = f"./static/upload/{i.email}"
            os.makedirs(save_path, exist_ok=True)

            # ...
            def _on_file(_file):
                files[_file.field_name] = {"name": _file.file_name}

                ext = PurePosixPath(_file.file_name.decode()).suffix
                file_path = f"{save_path}/{name}{ext}"

                if ext not in (".png", ".jpg", ".jpeg"):
                    return "Format files: (png, jpg, jpeg)..!"
                    
                with open(file_path, "wb") as fle:
                    fle.write(_file.file_object.getbuffer())

                    img_size = Image.open(file_path)
                    # ..
                    basewidth = 256
                    wpercent = basewidth / float(img_size.size[0])
                    hsize = int((float(img_size.size[1]) * float(wpercent)))
                    # ..
                    img_resize = img_size.resize((basewidth, hsize), Image.Resampling.LANCZOS)
                    img_resize.save(file_path)

                print("_file", _file)
            # ...

            body = io.BytesIO(bytearray(request.body))
            parse_form(headers, body, on_field=_on_filed, on_file=_on_file)

            # ...
            obj = files[b"file"]["name"].decode()
            ext = PurePosixPath(obj).suffix
            str_path = f"{save_path}/{name}{ext}"

            print("fields..", fields)
            print("files..", files)

            # ..
            file_query = (
                sqlalchemy_update(User)
                .where(User.id == id)
                .values(
                    file=str_path.replace(".", "", 1),
                    modified_at=datetime.now(),
                )
                .execution_options(synchronize_session="fetch")
            )
            # ..
            await session.execute(file_query)
            await session.commit()

            return Response(
                status_code=302,
                headers={
                    "location": quote(
                        f"/auth/details/{id }",
                        safe=":/%#?=@[]!$&'()*+,;",
                    )
                },
                description=("Ok..!"),
            )


@auth.get("/update-del/:id")
@visited()
# ...
async def get_del_bool(request):
    # ..
    id = request.path_params["id"]
    user = await get_token_visited_payload(request)
    template = "/auth/del_bool.html"

    async with async_session() as session:
        # ..
        i = await left_right_first(session, User, User.id, user["user_id"])
        # ..
        if user["user_id"] == i.id:
            if Path(f"./static/upload/{i.email}").exists():
                all_img = list(Path(f"./static/upload/{i.email}").iterdir())
                context = {
                    "request": request,
                    "i": i,
                    "all_img": all_img,
                }
                return templates.render_template(template, **context)
            return "not img..!"
        return "You are banned - this is not your account..!"


@auth.post("/update-del/:id")
# ...
async def img_del_bool(request):
    # ..
    id = request.path_params["id"]
    user = await get_token_visited_payload(request)

    async with async_session() as session:
        # ..
        i = await left_right_first(session, User, User.id, user["user_id"])
        # ..
        if user["user_id"] == i.id:
            # ..
            obj = dict(urllib.parse.parse_qs(request.body))
            print(" body..", obj)
            # ..
            if obj.get("del_bool") == "on":
                # ..
                if Path(f".{i.file}").exists():
                    Path.unlink(f".{i.file}")
                # ..
                fle_not = (
                    sqlalchemy_update(User)
                    .where(User.id == id)
                    .values(file=None, modified_at=datetime.now())
                    .execution_options(synchronize_session="fetch")
                )
                await session.execute(fle_not)
                await session.commit()
                # ..
                return Response(
                    status_code=302,
                    headers={
                        "location": quote(
                            f"/auth/details/{id }",
                            safe=":/%#?=@[]!$&'()*+,;",
                        )
                    },
                    description=("Ok..!"),
                )

            if obj.get("del_img"):
                # ..
                print("img del_img", obj["del_img"])
                print([path for path in obj["del_img"] if Path(path).exists()])
                print("OK..!")
                i_list = [path for path in obj["del_img"] if Path(path).exists()]

                for itm in i_list:
                    Path.unlink(itm)

                return Response(
                    status_code=302,
                    headers={
                        "location": quote(
                            f"/auth/details/{id }",
                            safe=":/%#?=@[]!$&'()*+,;",
                        )
                    },
                    description=("Ok..!"),
                )

            return Response(
                status_code=302,
                headers={
                    "location": quote(
                        f"/auth/details/{id }",
                        safe=":/%#?=@[]!$&'()*+,;",
                    )
                },
                description=("Ok..!"),
            )


@auth.get("/logout")
@visited()
# ...
async def get_user_logout(request):
    # ..
    user = await get_token_visited_payload(request)
    template = "/auth/logout.html"

    async with async_session() as session:
        # ..
        i = await left_right_first(session, User, User.id, user["user_id"])
        # ..
        if user["user_id"] == i.id:
            context = {
                "request": request,
                "i": i,
            }
            return templates.render_template(template, **context)
        return "You are banned - this is not your account..!"


@auth.post("/logout")
# ...
async def user_logout(request):
    user = await get_token_visited_payload(request)
    # ..
    async with async_session() as session:
        # ..
        i = await left_right_first(session, User, User.id, user["user_id"])
        # ..
        if user["user_id"] == i.id:
            response = Response(
                status_code=302,
                headers={
                    "location": quote(
                        "/auth/list",
                        safe=":/%#?=@[]!$&'()*+,;",
                    )
                },
                description=("Ok..!"),
            )
            response.delete_cookie(key="visited", path="/")
            # ..
            return response


@auth.get("/email-verify")
async def verify_email(request):
    response = await mail_verify(request)
    return response


@auth.get("/email-verify-resend")
async def get_resend_email(request):
    template = "/auth/resend.html"
    context = {
        "request": request,
    }
    return templates.render_template(template, **context)


@auth.post("/email-verify-resend")
async def resend_email(request):
    async with async_session() as session:
        # ..
        obj = dict(urllib.parse.parse_qsl(request.body))
        # ..
        # ..
        user = await left_right_first(session, User, User.email, obj["email"])
        # ..
        if not user:
            return Response(
                status_code=401,
                headers={"accept": "text/plain"},
                description="Пользователь с таким адресом электронной почты не существует!",
            )
        if user.email_verified:
            return Response(
                status_code=400,
                headers={"accept": "text/plain"},
                description="Электронная почта уже проверена!",
            )
        # ..
        payload = {
            "email": obj["email"],
            "exp": datetime.utcnow()
            + timedelta(minutes=int(EMAIL_TOKEN_EXPIRY_MINUTES)),
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, key, algorithm)
        verify = obj["email"]
        await verify_mail(
            f"Follow the link, confirm your email - {request.url.scheme}://{request.url.host}/auth/email-verify?token={token}",
            verify,
        )


@auth.get("/reset-password")
async def get_reset_password(request):
    # ..
    template = "/auth/reset-password.html"
    context = {
        "request": request,
    }
    return templates.render_template(template, **context)


@auth.post("/reset-password")
async def reset_password(request):
    async with async_session() as session:
        # ..
        obj = dict(urllib.parse.parse_qsl(request.body))
        # ..
        user = await left_right_first(session, User, User.email, obj["email"])
        # ..
        if not user:
            return Response(
                status_code=401,
                headers={"accept": "text/plain"},
                description="Пользователь с таким адресом электронной почты не существует!",
            )
        # ...
        token = await encode_reset_password(obj["email"])
        verify = obj["email"]
        await verify_mail(
            f"Follow the link, confirm your email - {request.url.scheme}://{request.url.host}/auth/reset-password-confirm?token={token}",
            verify,
        )

        response = "Ok..! Link to password recovery. Check email"
        return response


async def reset_password_verification(request):
    async with async_session() as session:
        email = await decode_reset_password(request)
        # ..
        user = await left_right_first(session, User, User.email, email)
        # ..
        if not user:
            return Response(
                status_code=401,
                headers={"accept": "text/plain"},
                description="Недействительный пользователь..! Пожалуйста, создайте учетную запись",
            )
        # ..
        obj = dict(urllib.parse.parse_qsl(request.body))
        # ..
        user.password = pbkdf2_sha1.hash(obj["password"])
        await session.commit()


@auth.get("/reset-password-confirm")
async def get_reset_password_confirm(request):
    template = "auth/reset-password-confirm.html"
    context = {
        "request": request,
    }
    return templates.render_template(template, **context)


@auth.post("/reset-password-confirm")
async def reset_password_confirm(request):
    await reset_password_verification(request)
    return Response(
        status_code=302,
        headers={
            "location": quote(
                str("/auth/login"),
                safe=":/%#?=@[]!$&'()*+,;",
            )
        },
        description=("Ok..!"),
    )


@auth.get("/delete/{:id}")
@visited()
# ...
async def get_user_delete(request):
    # ..
    id = request.path_params["id"]
    user = await get_token_visited_payload(request)
    template = "/auth/delete.html"

    async with async_session() as session:
        # ..
        i = await left_right_first(session, User, User.id, user["user_id"])
        # ..
        if user["user_id"] == i.id:
            context = {
                "request": request,
                "i": i,
            }
            return templates.render_template(template, **context)
        return "You are banned - this is not your account..!"


@auth.post("/delete/{:id}")
@visited()
# ...
async def user_delete(request):
    # ..
    id = request.path_params["id"]
    user = await get_token_visited_payload(request)

    async with async_session() as session:
        if user["user_id"] == i.id:
            i = await left_right_first(session, User, User.id, user["user_id"])
            await img.del_user(i.email)
            # ..
            await session.delete(i)
            await session.commit()
            # ..
            return Response(
                status_code=302,
                headers={
                    "location": quote(
                        "/auth/list",
                        safe=":/%#?=@[]!$&'()*+,;",
                    )
                },
                description=("Ok..!"),
            )


@auth.get("/list")
async def user_list(request):
    # ..
    template = "/auth/list.html"

    async with async_session() as session:
        # ..
        stmt = await session.execute(select(User))
        result = stmt.scalars().all()
        # ..
        context = {
            "request": request,
            "result": result,
        }
        # ...
        if request.method == "GET":
            return templates.render_template(template, **context)


@auth.get("/details/:id")
async def get_user_detail(request):
    # ..
    id = request.path_params["id"]
    template = "/auth/details.html"

    async with async_session() as session:
        # ..
        i = await left_right_first(session, User, User.id, id)
        # ..
        if i:
            context = {
                "request": request,
                "i": i,
            }
            return templates.render_template(template, **context)
        return Response(
            status_code=302,
            headers={
                "location": quote(
                    str("/auth/list"),
                    safe=":/%#?=@[]!$&'()*+,;",
                )
            },
            description=("Ok..!"),
        )
