import requests
import re


class GithubClient():
    def __init__(self, token=None):
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers['Authorization'] = 'token {token}'.format(token=token)
        self.session.headers['Accept'] = 'application/vnd.github.black-cat-preview+json'

    def get_involved_pull_requests(self, username):
        tmpl = "https://api.github.com/search/issues?q=involves%3A{username}%20state%3Aopen%20type%3Apr&per_page=100"
        url = tmpl.format(username=username)
        return self._paginated_getter(url, subkey='items')

    def get_pr(self, owner, repo, number):
        tmpl = "https://api.github.com/repos/{owner}/{repo}/pulls/{number}"
        url = tmpl.format(owner=owner, repo=repo, number=number)
        return self._getter(url)

    def get_pr_reviews(self, owner, repo, number):
        tmpl = "https://api.github.com/repos/{owner}/{repo}/pulls/{number}/reviews"
        url = tmpl.format(owner=owner, repo=repo, number=number)
        return self._paginated_getter(url)

    def get_pr_commits(self, owner, repo, number):
        tmpl = "https://api.github.com/repos/{owner}/{repo}/pulls/{number}/commits"
        url = tmpl.format(owner=owner, repo=repo, number=number)
        return self._paginated_getter(url)

    def get_pr_comments(self, owner, repo, number):
        tmpl = "https://api.github.com/repos/{owner}/{repo}/pulls/{number}/comments"
        url = tmpl.format(owner=owner, repo=repo, number=number)
        return self._paginated_getter(url)

    def get_pr_info_from_link(self, pr_link):
        try:
            repo_match = re.search('https://github.com/(\S+)/(\S+)/pull/(\d+)', pr_link)
            return repo_match.groups()
        except Exception:
            # TODO: Log the exception
            return []

    def _getter(self, url):
        return self.json_response(self.session.get(url))

    def _paginated_getter(self, url, subkey=None):
        """ Pagination utility.  Obnoxious. """

        results = []
        link = dict(next=url)

        while 'next' in link:
            response = self.session.get(link['next'])
            json_res = self.json_response(response)

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
