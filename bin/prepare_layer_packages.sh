#!/usr/bin/env bash
###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

set -o errexit
set -o nounset
set -o pipefail

python_version="3.10"
current_dir="$PWD"
dir="$(basename "$current_dir")"

# Find the bin directory relative to the current location
# Look for project structure indicators rather than specific directory names
if [ -d "./bin" ] && [ -d "./infra" ]; then
    # We're in the project root
    pushd ./bin
elif [ -d "../bin" ] && [ -d "../infra" ]; then
    # We're one level down (like in infra/)
    pushd ../bin
elif [ -d "../../bin" ] && [ -d "../../infra" ]; then
    # We're two levels down (like in cdk_stack/, tests/, lambdas/)
    pushd ../../bin
elif [ "$dir" = "bin" ]; then
    # We're already in the bin directory
    pushd ./
else
    echo "Error: Could not locate the project structure. Please run this script from the project root or a known subdirectory."
    exit 1
fi

# we are in bin folder

#### common layer ####
echo -e "\n** Packaging common helpers into python folder..."
mkdir -p ../lambda_layer/common
pushd ../lambda_layer/common

if [ -d ./python ]
then
    rm -rf ./python
fi

mkdir -p ./python/common
cp ../../infra/lambdas/requirements.txt ./python/
cp ../../infra/lambdas/common/*.py ./python/common/

pip3 install \
  -t ./python \
  --implementation cp \
  --python-version $python_version \
  --platform manylinux2014_aarch64 \
  --only-binary=:all: --upgrade \
  --no-cache-dir \
  -r ./python/requirements.txt

# Clean any existing pip cache
pip cache purge
if [ -f common_layer.zip ]
then
    rm -rf common_layer.zip
fi

zip -rq common_layer.zip python -x "./**/__pycache__/*"

echo "common layer copied"
popd
