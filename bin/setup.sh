#!/bin/bash

###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###


current_dir="$PWD"
dir="$(basename "$current_dir")"

# check if current directory name ends with "xxx"
if [ "$dir" = "sample-empowering-air-quality-research-serverless-machine-learning-predictive-analytics" ]
then
    pushd ./
elif [ "$dir" = "infra" ]
then
    pushd ../
elif [ "$dir" = "cdk_stack"]
then
    pushd ../../
elif [ "$dir" = "tests" ]
then
    pushd ../../
elif [ "$dir" = "lambdas" ]
then
    pushd ../../
elif [ "$dir" = "bin" ]
then
    pushd ../
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment"
    python3 -m venv .venv
fi
source .venv/bin/activate

pip install -r infra/requirements.txt

sh ./bin/prepare_layer_packages.sh

popd

pushd infra

pushd scripts

python3 config.py --use-defaults
if [ $? -ne 0 ]; then
    echo "Error: config.py failed"
    exit 1
fi

popd

# To bootstrap the stack run following command
cdk bootstrap

# To synthesize the stack run following command
cdk synth

# To deploy the stack run following command
# cdk deploy --require-approval=never

popd
