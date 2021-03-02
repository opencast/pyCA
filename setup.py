from setuptools import setup, find_packages
import os

path = os.path.abspath(os.path.dirname(__file__))


def read(filename):
    with open(os.path.join(path, filename), encoding='utf-8') as f:
        return f.read()


setup(
    name="pyca",
    version="4.1",
    description="Opencast Capture Agent",
    author="Lars Kiesow",
    author_email='lkiesow@uos.de',
    license="LGPLv3",
    url="https://github.com/opencast/pyCA",
    long_description=read('README.rst'),
    long_description_content_type='text/x-rst',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pycurl>=7.19.5",
        "python-dateutil>=2.4.0",
        "configobj>=5.0.0",
        "sqlalchemy>=0.9.8",
        "sdnotify>=0.3.2",
        "psutil>=5.0.1",
        "flask>=1.0.2",
    ],
    entry_points={
        'console_scripts': [
            'pyca = pyca.__main__:main'
        ]
    },
    test_suite="tests",
)
