# -*- coding: utf-8 -*-
import requests
import re
import dateutil.parser
import datetime
from dateutil.tz import tzutc
import sys


class GithubClient():
    def __init__(self, token):
        self.token = token
        self.session = requests.Session()
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


TOKEN = 'e7070e8a08170ca71ec0ba5566b3a19989db6b26'
NEVER = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzutc())

if len(sys.argv) < 2:
    raise RuntimeError("Specify a username as a parameter")

USER = sys.argv[1]

client = GithubClient(token=TOKEN)
raw_prs = client.get_involved_pull_requests(USER)
pr_links = sorted([x['html_url'] for x in raw_prs])

prs_with_reviews = []

for pr_link in pr_links:
    owner, repo, number = client.get_pr_info_from_link(pr_link)

    pr_reviews_raw = client.get_pr_reviews(owner, repo, number)
    if not pr_reviews_raw:
        print("Skipping {}: no reviews found".format(pr_link))
        continue

    prs_with_reviews.append((pr_link, owner, repo, number, pr_reviews_raw))


for pr_link, owner, repo, number, pr_reviews_raw in prs_with_reviews:
    # Collect review results
    review_results = {}
    for pr_review in pr_reviews_raw:
        user = pr_review['user']['login']
        review_results[user] = {
            'state': pr_review['state'],
            'date': dateutil.parser.parse(pr_review['submitted_at'])
        }

    # Collect comments
    comments = []
    comments_raw = client.get_pr_comments(owner, repo, number)
    for comment in comments_raw:
        comments.append({
            'user': comment['user']['login'],
            'text': comment['body'],
            'date': dateutil.parser.parse(pr_review['submitted_at'])
        })

    print('------')
    # Print PR title and current user review stat
    pr_info_raw = client.get_pr(owner, repo, number)
    pr_title = pr_info_raw['title']
    print('{} - {}'.format(pr_link, pr_title))

    pr_owner = pr_info_raw['user']['login']
    print("PR Owner: {}".format(pr_owner))
    print("Reviews:")
    # Print others review state
    for pr_reviewer in review_results:
        pr_review_result = review_results[pr_reviewer]['state']
        print('\t {} - {}'.format(pr_reviewer, pr_review_result))

    # Find last user comment or review
    user_comments = filter(lambda x: x['user'] == USER, comments)
    sorted_user_comments = sorted(user_comments, key=lambda x: x['date'])
    last_user_comment_date = sorted_user_comments[-1]['date'] if sorted_user_comments else NEVER

    # print out new comments since last user activity
    new_comments = [x for x in comments if x['date'] > last_user_comment_date]
    if new_comments:
        print('\t New comments:')
        for comment in new_comments:
            print('\t\t{}: {}'.format(comment['user'], comment['text']))

    print('\n')
