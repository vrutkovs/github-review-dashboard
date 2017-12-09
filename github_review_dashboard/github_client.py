# -*- coding: utf-8 -*-
import requests
import re
import urllib.parse
from functools import lru_cache

# Types
from typing import List


class GithubClient():
    api_prefix = "https://api.github.com"

    def __init__(self, token=None):
        self.token = token
        self.total_count = 0
        self.session = requests.Session()
        if token:
            self.session.headers['Authorization'] = 'token {}'.format(token)
        self.session.headers['Accept'] = \
            'application/vnd.github.black-cat-preview+json'

    def get_involved_pull_requests(self, username):
        tmpl = "{prefix}/search/issues?{query}"
        query = {
            'q': 'involves:{} state:open type:pr'.format(username),
            'per_page': 100}
        url = tmpl.format(prefix=self.api_prefix,
                          query=urllib.parse.urlencode(query))
        return self._paginated_getter(url, subkey='items',
                                      set_total_count=True)

    @lru_cache(maxsize=64)
    def get_user_info(self, username):
        tmpl = "{prefix}/users/{username}"
        url = tmpl.format(prefix=self.api_prefix, username=username)
        return self._getter(url)

    def get_pr(self, owner, repo, number):
        tmpl = "{prefix}/repos/{owner}/{repo}/pulls/{number}"
        url = tmpl.format(prefix=self.api_prefix,
                          owner=owner, repo=repo, number=number)
        return self._getter(url)

    def get_pr_reviews(self, owner, repo, number):
        tmpl = "{prefix}/repos/{owner}/{repo}/pulls/{number}/reviews"
        url = tmpl.format(prefix=self.api_prefix,
                          owner=owner, repo=repo, number=number)
        return self._paginated_getter(url)

    def get_pr_commits(self, owner, repo, number):
        tmpl = "{prefix}/repos/{owner}/{repo}/pulls/{number}/commits"
        url = tmpl.format(prefix=self.api_prefix,
                          owner=owner, repo=repo, number=number)
        return self._paginated_getter(url)

    def get_pr_comments(self, owner, repo, number):
        tmpl = "{prefix}/repos/{owner}/{repo}/pulls/{number}/comments"
        url = tmpl.format(prefix=self.api_prefix,
                          owner=owner, repo=repo, number=number)
        return self._paginated_getter(url)

    def get_pr_review_requests(self, owner, repo, number):
        tmpl = "{prefix}/repos/{owner}/{repo}/" \
               "pulls/{number}/requested_reviewers"
        url = tmpl.format(prefix=self.api_prefix,
                          owner=owner, repo=repo, number=number)
        return self._paginated_getter(url)

    @staticmethod
    @lru_cache(maxsize=64)
    def get_pr_info_from_link(pr_link):
        try:
            repo_match = re.search('https://github.com/(\S+)/(\S+)/pull/(\d+)',
                                   pr_link)
            return repo_match.groups()
        except Exception:
            # TODO: Log the exception
            return []

    def _getter(self, url):
        return self.json_response(self.session.get(url))

    def _paginated_getter(self, url, subkey=None, set_total_count=False):
        """ Pagination utility.  Obnoxious. """

        results: List[str] = []
        link = dict(next=url)

        while 'next' in link:
            response = self.session.get(link['next'])
            json_res = self.json_response(response)

            if set_total_count:
                # Set client's 'total_count' var so we could display a
                # progress bar
                self.total_count = json_res['total_count']

            if subkey is not None:
                json_res = json_res[subkey]

            results += json_res

            link = self._link_field_to_dict(response.headers.get('link', None))

        return results

    @staticmethod
    def json_response(response):
        # If we didn't get good results, just bail.
        if response.status_code != 200:
            raise IOError(
                "Non-200 status code %r; %r; %r" % (
                    response.status_code, response.url, response.text,
                ))
        if callable(response.json):
            # Newer python-requests
            return response.json()
        else:
            # Older python-requests
            return response.json

    @staticmethod
    def _link_field_to_dict(field):
        """ Utility for ripping apart github's Link header field.
        It's kind of ugly.
        """

        if not field:
            return dict()

        return dict([
            (
                part.split('; ')[1][5:-1],
                part.split('; ')[0][1:-1],
            ) for part in field.split(', ')
        ])
