
import urllib.parse, json, websockets
from collections import defaultdict

from robyn import Request, SubRouter, jsonify, WebSocket
from robyn.robyn import Url

from db_config.storage_config import async_session

from account.opt_slc import visited, get_token_visited_payload

from options_select.opt_slc import templates, in_all, left_right_all, left_right_first

from account.models import User


chat = SubRouter(__name__, prefix="/chat")
websocket = WebSocket(chat, "/item")
websocket_state = defaultdict(int)
clients = set()


@websocket.on("connect")
async def connect(wst):
    return jsonify({"message":"connect Ok..!"})


@websocket.on("message")
async def chat_all(wst, msg: str) -> str:

    response: dict = {"ws_id": wst.id, "resp": "", "msg": msg}
    print(" response..", response)

    data = json.loads(msg)
    i = json.dumps(data)

    for client in [*clients]:
        client.async_send_to(wst.id, json.dumps(msg))

    wst.async_broadcast(i)

    return jsonify({"message":"message..!"})


@websocket.on("close")
async def close(wst):
    print(f"close.. {wst.id}")
    return str()


@chat.get("/foo")
def get_foo(request):
    template = "/chat/chat.html"
    context = {"request": request}
    template = templates.render_template(template, **context)
    return template

@chat.post("/foo")
def post_foo(request):
    # ..
    obj = dict(urllib.parse.parse_qsl(request.body))
    # ..
    return obj["message"]
