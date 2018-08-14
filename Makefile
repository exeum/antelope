.PHONY: build push deploy rm ps

build:
	docker build -t exeum/antelope-scraper scraper
	docker build -t exeum/antelope-deliverer deliverer

push:
	docker push exeum/antelope-scraper
	docker push exeum/antelope-deliverer

deploy:
	docker stack deploy -c docker-compose.yml antelope

rm:
	docker stack rm antelope

ps:
	docker stack ps antelope --no-trunc
