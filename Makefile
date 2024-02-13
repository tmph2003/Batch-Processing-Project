docker-start:
	docker compose up -d
python-installation:
	pip --timeout=1000 install --no-cache-dir -r /requirements.txt

up: docker-start
python: python-installation
