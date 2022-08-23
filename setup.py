import io
from setuptools import setup, find_packages

requirements = ["requests"]

# Use the README.md content for the long description:
with io.open("README.md", encoding="utf-8") as fo:
    long_description = fo.read()

pkg = "rifleman"
setup(
    name=pkg,
    version="0.1.9",
    url="https://github.com/seanbreckenridge/rifleman",
    author="Sean Breckenridge",
    author_email="seanbrecke@gmail.com",
    description=("""an extendible dispatcher to lint/format code, based on rifle"""),
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="https://raw.githubusercontent.com/ranger/ranger/master/LICENSE",
    packages=find_packages(include=[pkg]),
    package_data={pkg: ["py.typed"]},
    test_suite="tests",
    install_requires=requirements,
    keywords="lint",
    entry_points={"console_scripts": ["rifleman = rifleman.__main__:main"]},
    extras_require={
        "testing": [
            "pytest",
            "mypy",
        ]
    },
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
