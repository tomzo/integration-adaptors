#!/bin/bash -e

IMAGE_PREFIX=$1

if [ -z "$IMAGE_PREFIX" ]; then
  echo "Please specify one of the images to be built: inbound, outbound, or route"
  exit 5
fi

export BUILD_TAG=latest
export DOCKER_REGISTRY=327778747031.dkr.ecr.eu-west-2.amazonaws.com

eval $(aws ecr get-login --region eu-west-2 --no-include-email)

image_tag=$(git rev-parse HEAD)

packer build -except publish pipeline/packer/${IMAGE_PREFIX}.json

docker tag local/mhs-$IMAGE_PREFIX $DOCKER_REGISTRY/mhs-${IMAGE_PREFIX}:$image_tag

docker push $DOCKER_REGISTRY/mhs-${IMAGE_PREFIX}:$image_tag
