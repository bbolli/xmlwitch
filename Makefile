install:
	pwd=$$(pwd); \
	for py in ~/.local/lib/python3.*/site-packages/; do \
		cd $$py && rm -f xmlbuilder && ln -s $$pwd/xmlbuilder .; \
	done
