.PHONY: scraper deliverer deploy rm ps

scraper:
	cd scraper && \
	docker build -t scraper .

deliverer:
	cd deliverer && \
	docker build -t deliverer .

deploy:
	docker stack deploy -c docker-stack.yml crawler

rm:
	docker stack rm crawler

ps:
	docker stack ps --no-trunc crawler
