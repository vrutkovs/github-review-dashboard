FROM fedora:27

RUN dnf update -y --refresh && \
    dnf install -y git npm && \
    dnf clean all

ADD . /dash

ARG DEBUG

RUN cd /dash && \
    npm install patternfly@3.30.1 --save --prefix=github_review_dashboard/static && \
    pip3 install -r requirements.txt && \
    if [ -n $DEBUG ]; then pip3 install -r requirements_dev.txt; fi && \
    git log -1 --pretty=format:'%h' --abbrev-commit > github_review_dashboard/templates/commit.jinja2

WORKDIR /dash/github_review_dashboard

EXPOSE 8080

CMD ["python3", "github_reviews_web.py"]
