install:
	for py in ~/.local/lib/python3.*/site-packages/; do \
		cp xmlbuilder.py $$py/xmlbuilder.py; \
	done
