# -*- coding: utf-8 -*-
import sys
from github_reviews import make_report

if len(sys.argv) < 2:
    raise RuntimeError("Specify a username as a parameter")

user = sys.argv[1]

report = make_report(user)

for entry in report:
    print("------")
    print('{} - {}'.format(entry['pr_link'], entry['pr_title']))
    print("PR Owner: {}".format(entry['pr_owner']))

    print("Reviews:")
    for reviewer, result in entry['pr_reviews'].items():
        print('\t {} - {}'.format(reviewer, result))

    if entry['new_comments']:
        print("New comments:")
        for comment in entry['new_comments']:
            print('\t{}: {}'.format(comment['user'], comment['text']))

    if entry['new_commits']:
        print("New commits:")
        for commit in entry['new_commits']:
            print('\t{}: "{}" by {}'.format(
                commit['hash'], commit['message'], commit['user']))
    print("\n")
