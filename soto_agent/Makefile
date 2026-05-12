# soto_agent — local + deploy workflow
#
# All targets run from the repo root (../) since the agent is installed as a
# package via hatchling. Run with:
#
#   cd soto_agent && make <target>
# or
#   make -C soto_agent <target>
#
# Required env for deploy targets: AZ_SUB, AZ_RG, ACR_NAME, ACA_NAME.

REPO_ROOT := $(abspath $(CURDIR)/..)
GLOSSARY_SOURCE := $(HOME)/BCC_NGST_CG/docs/reference/ubiquitous-language.md
GLOSSARY_DEST := $(CURDIR)/data/ubiquitous-language.md

AZ_SUB ?= cebd9dd6-bc18-4e1c-9564-bd4ec13c565b
AZ_RG ?= BBC-ITBS-POC-EastUS
ACR_NAME ?= bbcsotoacr
ACA_NAME ?= soto-agent
IMAGE_TAG ?= latest

.PHONY: help test refresh-glossary vault prep image deploy run clean

help:
	@echo "soto_agent make targets:"
	@echo "  test              run pytest against soto_agent/tests/"
	@echo "  refresh-glossary  copy current ubiquitous-language.md from BCC_NGST_CG into soto_agent/data/"
	@echo "  vault             regenerate soto_agent/data/vault/ subset from local Obsidian vault"
	@echo "  prep              refresh-glossary + vault (everything Docker needs to COPY)"
	@echo "  image             prep + az acr build (pushes new container image to $(ACR_NAME))"
	@echo "  deploy            image + az containerapp update (rolls the new image to $(ACA_NAME))"
	@echo "  run               local FastAPI server via uvicorn on :8000"
	@echo "  clean             remove generated build artifacts (data/vault/)"

test:
	cd $(REPO_ROOT) && uv run pytest soto_agent/tests/ -v

refresh-glossary:
	@if [ ! -f "$(GLOSSARY_SOURCE)" ]; then \
		echo "ERROR: $(GLOSSARY_SOURCE) not found. Is BCC_NGST_CG checked out?"; \
		exit 1; \
	fi
	cp "$(GLOSSARY_SOURCE)" "$(GLOSSARY_DEST)"
	@echo "Glossary refreshed: $(GLOSSARY_DEST)"

vault:
	cd $(REPO_ROOT) && uv run python -m soto_agent.scripts.build_vault_subset

prep: refresh-glossary vault
	@echo "Build prep complete. Ready for 'make image'."

image: prep
	cd $(REPO_ROOT) && az acr build \
		--subscription $(AZ_SUB) \
		--registry $(ACR_NAME) \
		--image soto-agent:$(IMAGE_TAG) \
		--file soto_agent/Dockerfile \
		.

deploy: image
	az containerapp update \
		--subscription $(AZ_SUB) \
		--resource-group $(AZ_RG) \
		--name $(ACA_NAME) \
		--image $(ACR_NAME).azurecr.io/soto-agent:$(IMAGE_TAG)

run:
	cd $(REPO_ROOT) && uv run uvicorn soto_agent.server:app --reload --port 8000

clean:
	rm -rf $(CURDIR)/data/vault/
	@echo "Removed $(CURDIR)/data/vault/"
