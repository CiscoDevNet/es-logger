#!/bin/bash -xeu

# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

export PATH=${PATH}:~/.local/bin
pip install -q --user -r test-requirements.txt

TOXENV=flake8
for version in $(sed -n 's/[[:space:]]*- python:\(.*\)/\1/pg' .travis.yml | tr -d ' ')
do
    [[ -s "$(which python$version)" ]] && \
        TOXENV=${TOXENV}${TOXENV:+,}py$(echo $version | tr -d '.')
done

TOXENV=$TOXENV $HOME/.local/bin/tox --workdir /tmp
