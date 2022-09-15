from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in erpnext_dhlshipping/__init__.py
from erpnext_dhlshipping import __version__ as version

setup(
	name="erpnext_dhlshipping",
	version=version,
	description="DHL Shipping service for ERPNext",
	author="Bogdan Trajkovic",
	author_email="pthemes.developer@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
