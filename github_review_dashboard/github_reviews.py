# -*- coding: utf-8 -*-
import dateutil.parser
import datetime
import sys
import os

from dateutil.tz import tzutc

from github_client import GithubClient


TOKEN = None
NEVER = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzutc())

if len(sys.argv) < 2:
    raise RuntimeError("Specify a username as a parameter")

token_file_path = os.path.join(os.getcwd(), 'token')
if not os.path.exists(token_file_path):
    print("Auth token not found, please create a new token at Settings - Personal access tokens and put it in 'token' file")
else:
    with open(token_file_path, "r") as token_file:
        TOKEN = token_file.read().strip()

USER = sys.argv[1]


def make_report():
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
                'date': dateutil.parser.parse(comment['created_at'])
            })

        # Collect commits
        commits = []
        commits_raw = client.get_pr_commits(owner, repo, number)
        for commit in commits_raw:
            commits.append({
                'hash': commit['sha'][:8],
                'message': commit['commit']['message'].split('\n')[0],
                'user': commit['commit']['author']['name'],
                'date': dateutil.parser.parse(commit['commit']['author']['date'])
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
            print('New comments:')
            for comment in new_comments:
                print('\t{}: {}'.format(comment['user'], comment['text']))

        # print new commits since last activity
        new_commits = [x for x in commits if x['date'] > last_user_comment_date]
        if new_commits:
            print('New commits:')
            for commit in new_commits:
                print('\t{}: "{}" by {}'.format(
                    commit['hash'], commit['message'], commit['user']))

        print('\n')

make_report()
