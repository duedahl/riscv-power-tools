SHELL := /bin/bash

activate:
	./util_scripts/activate.sh

deactivate:
	./util_scripts/deactivate.sh

jupyter:
	cd chipwhisperer/jupyter && \
	source $$(pyenv prefix cw)/bin/activate && \
	jupyter notebook