
from datetime import datetime

import urllib.parse, json
from collections import defaultdict

from robyn import Request, SubRouter, jsonify, WebSocket

from db_config.storage_config import async_session

from account.opt_slc import visited, get_token_visited_payload

from options_select.opt_slc import templates, in_all, left_right_all, left_right_first

from account.models import User
from chat.models import MessageChat


chat = SubRouter(__name__, prefix="/chat")
websocket = WebSocket(chat, "/item")
websocket_state = defaultdict(int)
clients = set()


@websocket.on("connect")
async def connect(wst):

    return jsonify(
        {"message":'',"owner_email": datetime.now().strftime("%H:%M:%S"),}
    )


@websocket.on("message")
async def chat_all(wst, msg: str) -> str:

    data = json.loads(msg)
    i = json.dumps(data)

    for client in [*clients]:
        client.async_send_to(wst.id, json.dumps(msg))

    async with async_session() as session:
        new = MessageChat()
        new.owner = data["owner"]
        new.owner_email = data["owner_email"]
        new.message = data["message"]
        new.created_at = datetime.now()
        # ..
        session.add(new)
        await session.commit()

    wst.async_broadcast(i)

    return jsonify({"message":'',"owner":'',"owner_email": data["owner_email"]})


@websocket.on("close")
async def close(wst):
    print(f"close.. {wst.id}")
    return str()


@chat.get("/foo")
@visited()
async def get_foo(request):
    user = await get_token_visited_payload(request)
    async with async_session() as session:
        result = await in_all(session, MessageChat)

    template = "/chat/chat.html"
    context = {"request": request, "result": result, "user": user}
    template = templates.render_template(template, **context)
    return template
