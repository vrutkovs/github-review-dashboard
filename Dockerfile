FROM fedora:27

ARG DEBUG

RUN dnf update -y --refresh && \
    dnf install -y git npm && \
    if [ -n $DEBUG ]; then dnf install -y python3-devel gcc redhat-rpm-config; fi && \
    dnf clean all

ADD . /dash

RUN cd /dash && \
    npm install patternfly@3.30.1 --save --prefix=github_review_dashboard/static && \
    pip3 install -r requirements.txt && \
    if [ -n $DEBUG ]; then pip3 install -r requirements_dev.txt; fi && \
    git log -1 --pretty=format:'%h' --abbrev-commit > github_review_dashboard/templates/commit.jinja2

WORKDIR /dash/github_review_dashboard

EXPOSE 8080

CMD ["python3", "github_reviews_web.py"]
