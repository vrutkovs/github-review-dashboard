# -*- coding: utf-8 -*-
from aiohttp import web
import aiohttp_jinja2
import jinja2

import github_reviews

async def root(request):
    return web.Response(text="Please open /<username> page")

@aiohttp_jinja2.template('user.jinja2')
async def user_report(request):
    user = request.match_info['user']
    return {
        'user': user,
        'items': github_reviews.make_report(user)
    }

app = web.Application(debug=True)
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))
app.router.add_static('/static/', path='static', show_index=True)

app.router.add_route('*', '/', root)
app.router.add_route('GET', '/{user}', user_report)

web.run_app(app)
