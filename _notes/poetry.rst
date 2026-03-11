install
-------

poetry install --only main
poetry install --with dev
poetry add --group dev package@latest


update
------

poetry cache clear pypi --all
poetry add vhelpers@latest
poetry show vhelpers


uninstall
---------

poetry remove vhelpers
poetry show --tree
poetry show --tree | findstr ciscoconfparse


venv
-----

C:\Users\inara\AppData\Local\pypoetry\Cache\virtualenvs
