.PHONY: build push

build:
	( cd scraper && docker build -t exeum/antelope-scraper . )
	( cd deliverer && docker build -t exeum/antelope-deliverer . )

push:
	docker push exeum/antelope-scraper
	docker push exeum/antelope-deliverer
