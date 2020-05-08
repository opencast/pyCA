from setuptools import setup, find_packages

setup(
    name="pyca",
    version="2.2",
    description="Opencast Capture Agent",
    author="Lars Kiesow",
    author_email='lkiesow@uos.de',
    license="LGPLv3",
    url="https://github.com/opencast/pyCA",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pycurl>=7.19.5",
        "python-dateutil>=2.4.0",
        "configobj>=5.0.0",
        "sqlalchemy>=0.9.8",
        "sdnotify>=0.3.2",
        "flask"
    ],
    entry_points={
        'console_scripts': [
            'pyca = pyca.__main__:main'
        ]
    },
    test_suite="tests",
)
