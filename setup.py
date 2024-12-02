from setuptools import setup


with open("README.md", "r", encoding="utf-8") as readme:
    long_description = readme.read()


setup(
    name="afdko-python-modules",
    use_scm_version=True,
    description="Tools for writing GOADB, kern feature, and mark feature files",
    long_description=long_description,
    author="Frank Grießhammer",
    author_email="afdko@adobe.com",
    url="https://github.com/adobe-type-tools/python-modules",
    license="MIT License",
    platforms=["Any"],
    setup_requires=["setuptools_scm"],
    python_requires=">=3.6",
    py_modules=[
        "goadbWriter",
        "kernFeatureWriter",
        "markFeatureWriter",
    ],
    entry_points={
        'console_scripts': [
            'goadbWriter=goadbWriter:main',
            'kernFeatureWriter=kernFeatureWriter:main',
            'markFeatureWriter=markFeatureWriter:main',
        ],
    },
    install_requires=["afdko"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Text Processing :: Fonts",
    ]
)
