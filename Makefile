IMAGE ?= langextract-api:latest

build:
	docker build -t $(IMAGE) .

run:
	docker run --rm -p 8080:8080 \
		-e CLIENT_API_KEY=$${GEMINI_API_KEY} \
		-e MODEL_ID=$${MODEL_ID:-gemini-2.5-flash} \
		-v $$(pwd)/artifacts:/artifacts \
		$(IMAGE)

test-extract:
	curl -s -X POST localhost:8080/extract \
		-H 'content-type: application/json' \
		-d @examples/config.sample.json | jq .

test-visualize:
	curl -s -X POST localhost:8080/visualize \
		-H 'content-type: application/json' \
		-d @examples/config.sample.json | jq .
