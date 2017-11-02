set -eux

image="vrutkovs/github-review-dash"
container=$(buildah from scratch)
mnt=$(buildah mount $container)

dnf install --installroot $mnt --releasever 26 --setopt install_weak_deps=false -y \
  glibc-minimal-langpack python3
rpm --root=$mnt -e --nodeps \
  python3-pip python3-setuptools bash

mkdir -p $mnt/dash
cp -rf . $mnt/dash
pip3 install -r requirements.txt --no-cache-dir --ignore-installed --target=$mnt/usr/lib/python3.6/site-packages
npm install patternfly@3.25.1 --save --prefix=$mnt/dash/github_review_dashboard/static
git log -1 --pretty=format:'%h' --abbrev-commit > $mnt/dash/github_review_dashboard/templates/commit.jinja2
rm -rf $mnt/var/cache $mnt/var/log/hawkey.log $mnt/var/log/dnf*.log

buildah config \
    --cmd "python3 github_reviews_web.py" \
    --author "vrutkovs@redhat.com" \
    --label name=$image \
    --port 8080 \
    --workingdir='/dash/github_review_dashboard' \
    $container

buildah unmount $container
buildah commit $container $image
buildah rm $container

buildah push $image docker-daemon:$image:latest
