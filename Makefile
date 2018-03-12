.PHONY: build

build:
	( cd book && docker build -t exeum/antelope-book . )
	( cd trades && docker build -t exeum/antelope-trades . )
	( cd deliverer && docker build -t exeum/antelope-deliverer . )
