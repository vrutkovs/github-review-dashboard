# -*- coding: utf-8 -*-
import dateutil.parser
import datetime
import os
import logging
import sys

from dateutil.tz import tzutc

from github_review_dashboard.github_client import GithubClient

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(name)-25s: %(filename)s:%(lineno)-3d: %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)
logger = logging.getLogger('github_reviews')

NEVER = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzutc())

TOKEN = None

if 'TOKEN' in os.environ:
    TOKEN = os.environ['TOKEN']
else:
    print("Auth token not found, "
          "please create a new token at Settings - 'Personal access tokens' "
          "and set TOKEN env var")


def get_prs(client, user):
    logger.debug("get_prs for user {}".format(user))
    raw_prs = client.get_involved_pull_requests(user)
    # Sort PRs by date - most likely the newest were not reviewed
    sorted_prs = sorted(raw_prs, reverse=True,
                        key=lambda x: dateutil.parser.parse(x['updated_at']))
    pr_links = [x['html_url'] for x in sorted_prs]
    logger.debug("pr_links: {}".format(pr_links))

    for pr_link in pr_links:
        owner, repo, number = GithubClient.get_pr_info_from_link(pr_link)
        logger.debug("pr_links {}, owner {}, repo {}, number {}".format(
            pr_link, owner, repo, number))

        pr_reviews_raw = client.get_pr_reviews(owner, repo, number)
        yield (pr_link, owner, repo, number, pr_reviews_raw)


def get_pr_reviews(pr_reviews_raw):
    logger.debug("get_pr_reviews")
    review_results = {}
    pr_reviews_sorted = sorted(pr_reviews_raw,
                               key=lambda x:
                               dateutil.parser.parse(x['submitted_at']))
    for pr_review in pr_reviews_sorted:
        user = pr_review['user']['login']
        logger.debug("pr for user {} with state {}".format(
            user, pr_review['state']))

        # Don't replace approved/changes_required with 'commented'
        # Github API quirk probably
        existing_review = review_results.get(user, {}).get('state')
        logger.debug("pr state {}".format(existing_review))
        if existing_review in ['APPROVED', 'CHANGES_REQUESTED'] and \
           pr_review['state'] == 'COMMENTED':
            continue

        review_results[user] = {
            'state': pr_review['state'],
            'date': dateutil.parser.parse(pr_review['submitted_at'])
        }
    logger.debug(review_results)
    return review_results


def get_pr_review_reqs(client, owner, repo, number):
    requests_raw = client.get_pr_review_reqs(owner, repo, number)
    return [x['login'] for x in requests_raw]


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


def prepare_report(user):
    client = GithubClient(token=TOKEN)
    return (client, get_prs(client, user))


def make_report(user, client, prs_with_reviews):
    total_prs = None
    for i, pr_data in enumerate(prs_with_reviews):
        if not total_prs:
            total_prs = client.total_count

        progress = int(((i + 1) / total_prs) * 100)
        yield {'progress': progress}

        pr_link, owner, repo, number, pr_reviews_raw = pr_data
        logger.debug("PR {}".format(pr_link))

        pr_info_raw = client.get_pr(owner, repo, number)

        review_requested_from_users = \
            get_pr_review_reqs(client, owner, repo, number)
        review_results = get_pr_reviews(pr_reviews_raw)
        comments = get_pr_comments(client, owner, repo, number)
        commits = get_pr_commits(client, owner, repo, number)

        report_entry = {
            'pr_link': pr_link,
            'owner': owner,
            'repo': repo,
            'pr_number': number,
            'pr_title': pr_info_raw['title'],
            'pr_owner': pr_info_raw['user']['login'],
            'pr_reviews': {},
            'new_comments': [],
            'new_commits': []
        }

        # If user was explicitely requested to review it - show it
        user_was_requested_to_review = user in review_requested_from_users

        # Print others review state
        for pr_reviewer in review_results:
            pr_review_result = review_results[pr_reviewer]['state']
            report_entry['pr_reviews'][pr_reviewer] = pr_review_result

        # Add requests from other users unless there is a review set already
        for pr_review_req in review_requested_from_users:
            if pr_review_req not in report_entry['pr_reviews'].keys():
                report_entry['pr_reviews'][pr_review_req] = 'REVIEW_REQUESTED'

        last_review_date = review_results.get(user, {}).get('date') or NEVER

        # Find last user comment
        user_comments = filter(lambda x: x['user'] == user, comments)
        sorted_user_comments = sorted(user_comments, key=lambda x: x['date'])
        last_user_comment_date = sorted_user_comments[-1]['date'] \
            if sorted_user_comments else NEVER
        logger.debug("last_user_comment_date {}".format(
            last_user_comment_date))

        # Get user email so we could filter out new commits by this user
        user_info_raw = client.get_user_info(user)
        user_email = user_info_raw['email']

        user_commits = filter(lambda x: x['user_email'] == user_email, commits)
        sorted_user_commits = sorted(user_commits, key=lambda x: x['date'])
        last_user_commit_date = sorted_user_commits[-1]['date'] \
            if sorted_user_commits else NEVER
        logger.debug("last_user_commit_date {}".format(last_user_commit_date))

        # If last activity date cannot be found the PR should be skipped
        if not user_was_requested_to_review and \
           last_user_comment_date == NEVER and \
           last_review_date == NEVER and \
           last_user_commit_date == NEVER:
            continue

        last_user_activity = max([
            last_user_comment_date,
            last_review_date,
            last_user_commit_date
        ])
        logger.debug("last_user_activity {}".format(last_user_activity))

        #  Collect new comments since last user activity
        new_comments = [x for x in comments if x['date'] > last_user_activity]
        for comment in new_comments:
            report_entry['new_comments'].append({
                'date': comment['date'],
                'user': comment['user'],
                'text': comment['text']
            })
        logger.debug("new_comments {}".format(new_comments))

        # Collect new commits since last activity
        new_commits = [x for x in commits
                       if x['date'] > last_user_activity]
        for commit in new_commits:
            report_entry['new_commits'].append({
                'hash': commit['hash'],
                'user': commit['user'],
                'message': commit['message'],
                'date': commit['date']
            })
        logger.debug("new_commits {}".format(new_commits))

        # Skip PR if no new comments/commits available
        if user_was_requested_to_review or \
           report_entry['new_comments'] or \
           report_entry['new_commits']:
            yield report_entry
