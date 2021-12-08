#!/usr/bin/env bash

# generate new aws password token - needed for pushing to our aws acct
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 529675500956.dkr.ecr.us-east-2.amazonaws.com

# build image - adaptation on docker build cmd to specify linux amd64 build (override mac m1 build issues)
docker buildx build --platform=linux/amd64 -t hnt-miner-tax .

# tag image with :lates
docker tag hnt-miner-tax:latest 529675500956.dkr.ecr.us-east-2.amazonaws.com/hnt-miner-tax:latest

# push up to aws ecr
docker push 529675500956.dkr.ecr.us-east-2.amazonaws.com/hnt-miner-tax:latest