# -*- coding: utf-8 -*-
from aiohttp import web, MsgType, WSCloseCode
import aiohttp_jinja2
import jinja2

import github_reviews

async def root(request):
    return web.Response(text="Please open /<username> page")


@aiohttp_jinja2.template('user.jinja2')
async def user_report(request):
    user = request.match_info['user']
    # TODO: read this from request.app.router
    ws_url = '/{user}/ws'.format(user=user)
    return {
        'user': user,
        'ws_url': ws_url,
    }

async def ws(request):
    user = request.match_info['user']
    ws = web.WebSocketResponse()
    request.app['websockets'].append(ws)
    await ws.prepare(request)
    (client, prs) = github_reviews.prepare_report(user)

    async for msg in ws:
        if msg.tp == MsgType.text:
            for item in github_reviews.make_report(user, client, prs):
                data = {'item': item}
                response = aiohttp_jinja2.render_template('card.jinja2',
                                                          request, data)
                ws.send_str(response.text)
            ws.send_str("end")
    return ws


async def on_shutdown(app):
    for ws in app['websockets']:
        await ws.close(code=WSCloseCode.GOING_AWAY,
                       message='Server shutdown')

app = web.Application(debug=True)
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))
app.router.add_static('/static/', path='static', show_index=True)

app.router.add_route('*', '/', root)
app.router.add_route('GET', '/{user}', user_report)
app.router.add_route('*', '/{user}/ws', ws)

app['websockets'] = []
app.on_shutdown.append(on_shutdown)

web.run_app(app)
