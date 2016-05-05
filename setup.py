from setuptools import setup

setup(
    name="pyca",
    version="1.0.0",
    description="Opencast Matterhorn capture agent",
    author="Lars Kiesow",
    author_email='lkiesow@uos.de',
    license="LGPLv3",
    url="https://github.com/lkiesow/pyCA",
    packages=["pyca"],
    install_requires=[
        "icalendar>=3.8.4",
        "pycurl>=7.19.5",
        "python-dateutil>=2.4.0",
        "configobj>=5.0.0",
        "flask"
    ],
    data_files=[("etc", ["etc/pyca.conf"])],
    entry_points={
        'console_scripts': [
            'pyca = pyca.__main__:main'
        ]
    }
)
