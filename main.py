import os, pathlib

from robyn import (
    Request,
    Response,
    Robyn,
    jsonify,
    serve_file,
    serve_html,
)

# ...
#from db_startup.db import on_app_startup
# ...

from account.views import auth
from account.models import User
from account.opt_slc import get_visited_user

from config.settings import BASE_DIR

from db_config.storage_config import async_session
from options_select.opt_slc import in_all, templates

app = Robyn(__file__)


async def startup_handler():
    print("Starting up")


@app.shutdown_handler
def shutdown_handler():
    print("Shutting down")


async def async_without_decorator():
    return "Success!"


app.add_directory(
    route="/static/",
    directory_path=os.path.join(BASE_DIR, "static"),
    index_file="",
)


@app.get("/messages")
async def messages(request):
    context = {"request": request}
    template = templates.render_template(template_name="messages.html", **context)
    return template


@app.get("/")
async def async_on_app_startup(request):
    # ..
    #await on_app_startup()
    # ..

    async with async_session() as session:
        result = await in_all(session, User)
        i = await get_visited_user(request, session)
    # ..
    context = {"request": request, "result": result, "i": i}
    template = templates.render_template(template_name="index.html", **context)
    return template


# ===== Main =====


def main():
    app.add_response_header("server", "robyn")
    app.startup_handler(startup_handler)
    app.include_router(auth)
    app.start(port=8080)


if __name__ == "__main__":
    main()
