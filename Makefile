SHELL=/bin/bash -O expand_aliases
PS_IP=192.168.1.100

run-in-docker: build-docker
	bash run-in-docker.sh

build-docker:
	HTTPS_PROXY=http://localhost:7890 docker build -t gt7-dashboard .

serve:
	uv run -m bokeh serve .

setup: deps car_lists

deps:
	uv pip install -r requirements.txt

car_lists:
	uv run helper/download_cars_csv.py

test: test_deps deps
	uv run -m pytest .

test_deps:
	uv pip install pytest
