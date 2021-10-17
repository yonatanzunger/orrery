#!/bin/bash

# numpy doesn't (yet) support 3.10
pyenv local 3.9.0

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
