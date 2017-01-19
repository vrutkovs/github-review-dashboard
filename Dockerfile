FROM fedora:25

RUN dnf update -y && \
    dnf install -y python3-pip git npm && \
    git clone https://github.com/vrutkovs/github-review-dashboard /dash && \
    pip3 install -r requirements.txt && \
    npm install -g bower && \
    bower install && \
    dnf clean all

WORKDIR /dash/github_review_dashboard
ADD token /dash/github_review_dashboard/github_review_dashboard

EXPOSE 8080

CMD ["python3", "github_reviews_web.py"]
