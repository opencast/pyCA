from setuptools import setup

setup(
    name="pyca",
    version="1.0.0",
    description="Opencast Capture Agent",
    author="Lars Kiesow",
    author_email='lkiesow@uos.de',
    license="LGPLv3",
    url="https://github.com/opencast/pyCA",
    packages=["pyca"],
    install_requires=[
        "pycurl>=7.19.5",
        "python-dateutil>=2.4.0",
        "configobj>=5.0.0",
        "sqlalchemy>=0.9.8",
        "flask"
    ],
    entry_points={
        'console_scripts': [
            'pyca = pyca.__main__:main'
        ]
    }
)
