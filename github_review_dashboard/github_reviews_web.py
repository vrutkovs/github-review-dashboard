# -*- coding: utf-8 -*-
from aiohttp import web
from pyannotate_runtime import collect_types
from aiohttp_sse import sse_response
import aiohttp_jinja2
import jinja2
import json
import os

import github_review_dashboard.github_reviews as github_reviews


async def root(request):
    return web.Response(text="Please open /<username> page")


@aiohttp_jinja2.template('user.jinja2')
async def user_report(request):
    user = request.match_info['user']
    return {
        'user': user,
        'ws_url': request.app.router['ws'].url_for(user=user),
    }


async def ws(request):
    async with sse_response(request) as ws:
        user = request.match_info['user']
        (client, prs) = github_reviews.prepare_report(user)
        for item in github_reviews.make_report(user, client, prs):
            if 'progress' in item:
                ws.send(json.dumps(item))
            else:
                data = {'item': item}
                card = aiohttp_jinja2.render_template('card.jinja2',
                                                      request, data)
                ws.send(json.dumps({'card': card.text}))
        ws.send(json.dumps({'end': 'true'}))
        ws.force_close()
    return ws


async def start_pyannotate(app):
    collect_types.resume()


async def finish_pyannotate(app):
    collect_types.pause()


def main():
    app = web.Application(debug=True)
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))
    app.router.add_static('/static/', path='static', show_index=True)

    app.router.add_route('*', '/', root)
    app.router.add_route('GET', '/{user}', user_report)
    app.router.add_route('GET', '/{user}/ws', ws, name='ws')

    if os.environ["DEBUG"]:
        app.on_startup.append(start_pyannotate)
        app.on_cleanup.append(finish_pyannotate)

    web.run_app(app)


if __name__ == '__main__':
    collect_types.init_types_collection()
    main()
    collect_types.dump_stats('type_info.json')
