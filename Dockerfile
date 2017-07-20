FROM fedora:26

RUN dnf update -y --refresh && \
    dnf install -y python3-pip git npm && \
    dnf clean all && \
    npm install -g bower

RUN git clone https://github.com/vrutkovs/github-review-dashboard /dash && \
    cd /dash && \
    pip3 install -r requirements.txt && \
    bower install --allow-root && \
    git log -1 --pretty=format:'%h' --abbrev-commit > github_review_dashboard/templates/commit.jinja2

WORKDIR /dash/github_review_dashboard

EXPOSE 8080

CMD ["python3", "github_reviews_web.py"]
