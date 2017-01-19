# -*- coding: utf-8 -*-
import dateutil.parser
import datetime
import os

from dateutil.tz import tzutc

from github_client import GithubClient


TOKEN = None
NEVER = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzutc())

token_file_path = os.path.join(os.getcwd(), 'token')
if not os.path.exists(token_file_path):
    print("Auth token not found, please create a new token at Settings - Personal access tokens and put it in 'token' file")
else:
    with open(token_file_path, "r") as token_file:
        TOKEN = token_file.read().strip()


def filter_prs_without_reviews(client, user):
    raw_prs = client.get_involved_pull_requests(user)
    pr_links = sorted([x['html_url'] for x in raw_prs])
    prs_with_reviews = []

    for pr_link in pr_links:
        owner, repo, number = client.get_pr_info_from_link(pr_link)

        pr_reviews_raw = client.get_pr_reviews(owner, repo, number)
        if not pr_reviews_raw:
            print("Skipping {}: no reviews found".format(pr_link))
            continue

        prs_with_reviews.append((pr_link, owner, repo, number, pr_reviews_raw))

    return prs_with_reviews


def get_pr_reviews(pr_reviews_raw):
    review_results = {}
    for pr_review in pr_reviews_raw:
        user = pr_review['user']['login']
        review_results[user] = {
            'state': pr_review['state'],
            'date': dateutil.parser.parse(pr_review['submitted_at'])
        }
    return review_results


def get_pr_comments(client, owner, repo, number):
    comments = []
    comments_raw = client.get_pr_comments(owner, repo, number)
    for comment in comments_raw:
        comments.append({
            'user': comment['user']['login'],
            'text': comment['body'],
            'date': dateutil.parser.parse(comment['created_at'])
        })
    return comments


def get_pr_commits(client, owner, repo, number):
    commits = []
    commits_raw = client.get_pr_commits(owner, repo, number)
    for commit in commits_raw:
        commits.append({
            'hash': commit['sha'][:8],
            'message': commit['commit']['message'].split('\n')[0],
            'user': commit['commit']['author']['name'],
            'user_email': commit['commit']['author']['email'],
            'date': dateutil.parser.parse(commit['commit']['author']['date'])
        })
    return commits


def make_report(user):
    report = []

    client = GithubClient(token=TOKEN)

    prs_with_reviews = filter_prs_without_reviews(client, user)

    for pr_data in prs_with_reviews:
        pr_link, owner, repo, number, pr_reviews_raw = pr_data

        pr_info_raw = client.get_pr(owner, repo, number)

        review_results = get_pr_reviews(pr_reviews_raw)
        comments = get_pr_comments(client, owner, repo, number)
        commits = get_pr_commits(client, owner, repo, number)

        report_entry = {
            'pr_link': pr_link,
            'pr_title': pr_info_raw['title'],
            'pr_owner': pr_info_raw['user']['login'],
            'pr_reviews': {},
            'new_comments': [],
            'new_commits': []
        }

        # Print others review state
        for pr_reviewer in review_results:
            pr_review_result = review_results[pr_reviewer]['state']
            report_entry['pr_reviews'][pr_reviewer] = pr_review_result

        # Find last user comment or review
        user_comments = filter(lambda x: x['user'] == user, comments)
        sorted_user_comments = sorted(user_comments, key=lambda x: x['date'])
        last_user_comment_date = sorted_user_comments[-1]['date'] if sorted_user_comments else NEVER
        last_user_review_date = review_results.get(user, {}).get('date', None) or NEVER

        last_user_activity = max([
            last_user_comment_date,
            last_user_review_date
        ])

        # print out new comments since last user activity
        new_comments = [x for x in comments if x['date'] > last_user_activity]
        for comment in new_comments:
            report_entry['new_comments'].append({
                'date': comment['date'],
                'user': comment['user'],
                'text': comment['text']
            })

        # Get user email so we could filter out new commits by this user
        user_info_raw = client.get_user_info(user)
        user_email = user_info_raw['email']

        # print new commits since last activity
        new_commits = [x for x in commits
            if x['date'] > last_user_activity and
               x['user_email'] != user_email]
        for commit in new_commits:
            report_entry['new_commits'].append({
                'hash': commit['hash'],
                'user': commit['user'],
                'message': commit['message']
            })

        # Skip PR if no new comments/commits available
        if report_entry['new_commits'] or report_entry['new_commits']:
            report.append(report_entry)

    return report
