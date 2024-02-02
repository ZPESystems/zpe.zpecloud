sanity:
	ansible-test sanity --color --truncate 0 -v \
		--exclude plugins/module_utils/vendor/ \
		--exclude scripts/ \
		--exclude tests/utils/ \
		--docker default \
		--allow-disabled

units:
	ansible-test units --color --truncate 0 -v \
		--docker default

integration:
	ansible-test integration --color --truncate 0 -v \
		--docker default \
		--allow-disabled

lint-python:
	flake8 .

lint-yaml:
	yamllint .
