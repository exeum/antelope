.PHONY: build push deploy rm ps

build:
	( cd scraper && docker build -t exeum/antelope-scraper . )
	( cd deliverer && docker build -t exeum/antelope-deliverer . )

push:
	docker push exeum/antelope-scraper
	docker push exeum/antelope-deliverer

deploy:
	docker stack deploy -c docker-stack.yml antelope

rm:
	docker stack rm antelope

ps:
	docker stack ps antelope --no-trunc
