install
-------

poetry install --only main
poetry install --with dev
poetry add --group dev package@latest

poetry add {package}~{version}  #latest  minor version
poetry add {package}^{version}  #latest major version


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

poetry shell  #go to venv

show
----

poetry show


C:\Users\inara\AppData\Local\pypoetry\Cache\virtualenvs
