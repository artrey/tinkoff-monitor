IMAGE_NAME:=artrey/tinkoff-backend:latest
TIME_MARK:=$(shell date +%FT%H-%M)

dumpdb:
	mkdir -p _dumps
	python manage.py dumpdata --indent 2 \
		--exclude auth.permission \
		--exclude contenttypes \
		--exclude admin.logentry \
		--exclude sessions.session \
		> _dumps/db-${TIME_MARK}.json

downloaddb:
	mkdir -p _dumps
	ssh tinkoff "docker exec -t tinkoff_backend_1 python manage.py dumpdata --indent 2 \
		--exclude auth.permission \
		--exclude contenttypes \
		--exclude admin.logentry \
		--exclude sessions.session \
		> server-db-${TIME_MARK}.json"
	scp tinkoff:server-db-${TIME_MARK}.json _dumps/

build:
	docker build -t ${IMAGE_NAME} .

celery:
	PATH=${PWD}/apps/tasks/assets/:${PATH} celery -A tinkoff worker --loglevel debug --pool=solo

beat:
	celery -A tinkoff beat --loglevel debug
