import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="RISMA",
    version="0.0.1",
    author="Morteza Khazaei",
    author_email="khazaei.morteza@ut.ac.ir",
    description="Agriculture and Agri-Food Canada (AAFC)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Morteza-Khazaei/RISMA",
    project_urls={
        "Bug Tracker": "https://github.com/Morteza-Khazaei/RISMA/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)
