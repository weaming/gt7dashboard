SHELL=/bin/bash -O expand_aliases
PS_IP=192.168.1.100

run-in-docker: build-docker
	bash run-in-docker.sh

build-docker:
	HTTPS_PROXY=http://localhost:7890 docker build -t gt7-dashboard .

limited:
	GT7_LIMITED=true uv run gt7telemetry.py ${PS_IP}

race:
	BOKEH_LOG_LEVEL=fatal GT7_LIMITED=true GT7_HIDE_ANALYSIS=true GT7_HIDE_TUNING=true uv run gt7telemetry.py ${PS_IP}

serve:
	uv run -m bokeh serve .

normal:
	uv run gt7telemetry.py ${PS_IP}

setup: deps car_lists

deps:
	uv pip install -r requirements.txt

car_lists:
	uv run helper/download_cars_csv.py

test: test_deps deps
	uv run -m pytest .

test_deps:
	uv pip install pytest
