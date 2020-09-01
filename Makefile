SHELL := bash

.PHONY: venv check reformat

all: venv

venv:
	scripts/create-venv.sh

check:
	scripts/check-code.sh

reformat:
	scripts/format-code.sh
