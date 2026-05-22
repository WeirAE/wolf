"""
Basic setuptools configuration.

See https://setuptools.pypa.io/en/latest/userguide/quickstart.html#basic-use for information on
this standard setuptools file.

"""

from setuptools import setup


setup(
    name='wolf',
    version='0.0.1',
    install_requires=[
        'requests',
        'importlib-metadata; python_version<"3.10"',
    ],
    extras_require={
        'networkx':["networkx>=3.1"],
        'uwtools':["uwtools>=2.0"],
        'airflow':["apache-airflow>=2.8"],
        'full':["wolf[networkx,uwtools]"],
    }
)
