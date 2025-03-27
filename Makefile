.PHONY: prod preview


preview:
	@echo "Starting preview..."
	cd docs && quarto preview

prod:
	@echo "Building production site..."
	cd docs && quarto render

