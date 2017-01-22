# -*- coding: utf-8 -*-
import dateutil.parser
import datetime
import os

from dateutil.tz import tzutc

from github_client import GithubClient


NEVER = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzutc())

TOKEN = None

if 'TOKEN' in os.environ:
    TOKEN = os.environ['TOKEN']
else:
    print("Auth token not found, "
          "please create a new token at Settings - 'Personal access tokens' "
          "and set TOKEN env var")


def get_prs(client, user):
    raw_prs = client.get_involved_pull_requests(user)
    pr_links = sorted([x['html_url'] for x in raw_prs])

    for pr_link in pr_links:
        owner, repo, number = client.get_pr_info_from_link(pr_link)

        pr_reviews_raw = client.get_pr_reviews(owner, repo, number)
        yield (pr_link, owner, repo, number, pr_reviews_raw)


def get_pr_reviews(pr_reviews_raw):
    review_results = {}
    pr_reviews_sorted = sorted(pr_reviews_raw,
                               key=lambda x: dateutil.parser.parse(x['submitted_at']))
    for pr_review in pr_reviews_sorted:
        user = pr_review['user']['login']

        # Don't replace approved/changes_required with 'commented'
        # Github API quirk probably
        existing_review = review_results.get(user, {}).get('state', None)
        if existing_review in ['APPROVED', 'CHANGES_REQUESTED'] and \
           pr_review['state'] == 'COMMENTED':
            continue

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


def prepare_report(user):
    client = GithubClient(token=TOKEN)
    return (client, get_prs(client, user))


def make_report(user, client, prs_with_reviews):
    total_prs = None
    for i, pr_data in enumerate(prs_with_reviews):
        if not total_prs:
            total_prs = client.total_count

        progress = int(((i+1) / total_prs) * 100)
        yield {'progress': progress}

        pr_link, owner, repo, number, pr_reviews_raw = pr_data

        pr_info_raw = client.get_pr(owner, repo, number)

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

        # Print others review state
        for pr_reviewer in review_results:
            pr_review_result = review_results[pr_reviewer]['state']
            report_entry['pr_reviews'][pr_reviewer] = pr_review_result

        last_user_review_date = review_results.get(user, {}).get('date', None) or NEVER

        # Find last user comment
        user_comments = filter(lambda x: x['user'] == user, comments)
        sorted_user_comments = sorted(user_comments, key=lambda x: x['date'])
        last_user_comment_date = sorted_user_comments[-1]['date'] if sorted_user_comments else NEVER

        # Get user email so we could filter out new commits by this user
        user_info_raw = client.get_user_info(user)
        user_email = user_info_raw['email']

        user_commits = filter(lambda x: x['user_email'] == user_email, commits)
        sorted_user_commits = sorted(user_commits, key=lambda x: x['date'])
        last_user_commit_date = sorted_user_commits[-1]['date'] if sorted_user_commits else NEVER

        # If last activity date cannot be found the PR should be skipped
        if last_user_comment_date == NEVER and \
           last_user_review_date == NEVER and \
           last_user_commit_date == NEVER:
            continue

        last_user_activity = max([
            last_user_comment_date,
            last_user_review_date,
            last_user_commit_date
        ])

        #  Collect new comments since last user activity
        new_comments = [x for x in comments if x['date'] > last_user_activity]
        for comment in new_comments:
            report_entry['new_comments'].append({
                'date': comment['date'],
                'user': comment['user'],
                'text': comment['text']
            })

        # Collect new commits since last activity
        new_commits = [x for x in commits
                       if x['date'] > last_user_activity and
                       x['user_email'] != user_email]
        for commit in new_commits:
            report_entry['new_commits'].append({
                'hash': commit['hash'],
                'user': commit['user'],
                'message': commit['message'],
                'date': commit['date']
            })

        # Skip PR if no new comments/commits available
        if report_entry['new_commits'] or report_entry['new_commits']:
            yield report_entry
