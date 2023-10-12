from setuptools import setup

setup(
    name='gentainer',
    version='0.0.1',
    description='LXC containers in Gentoo',
    author='desultory',
    packages=['gentainer'],
    install_requires=[
        'pyroute2>=0.7.9',
        'portage>=3.0.52',
    ],
)
