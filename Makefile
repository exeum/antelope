.PHONY: scraper deliverer deploy rm ps

scraper:
	cd scraper && \
	docker build -t exeum/antelope-scraper .

deliverer:
	cd deliverer && \
	docker build -t exeum/antelope-deliverer .

deploy:
	docker stack deploy -c docker-stack.yml crawler

rm:
	docker stack rm crawler

ps:
	docker stack ps --no-trunc crawler
