FROM fedora:25

RUN dnf update -y && \
    dnf install -y python3-pip git npm && \
    git clone https://github.com/vrutkovs/github-review-dashboard /dash && \
    cd /dash && \
    pip3 install -r requirements.txt && \
    npm install -g bower && \
    bower install --allow-root && \
    dnf clean all

WORKDIR /dash/github_review_dashboard
ADD token /dash/github_review_dashboard/token

RUN git log -1 --pretty=format:'%h - %s' --abbrev-commit > templates/commit.jinja2

EXPOSE 8080

CMD ["python3", "github_reviews_web.py"]
