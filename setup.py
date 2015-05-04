#!/usr/bin/env python
# coding=utf-8

from setuptools import setup, find_packages
import os

def _read(fn):
    path = os.path.join(os.path.dirname(__file__), fn)
    return open(path).read()

setup(
    name='spotify-ripper',
    version='1.2.0',
    packages=find_packages(exclude=["tests"]),
    scripts=['spotify_ripper/main.py'],
    include_package_data=True,
    zip_safe=False,

     # Executable
    entry_points={
        'console_scripts': [
            'spotify-ripper = main:main',
        ],
    },

    # Additional data
    package_data={
        '': ['README.rst', 'LICENCE']
    },

    # Requirements
    install_requires=[
        'pyspotify==2.0.0b4',
        'colorama>=0.3.3',
        'mutagen==1.28',
        'requests>=2.3.0'
    ],

    # Metadata
    author='James Newell',
    author_email='james.newell@gmail.com',
    description='a small ripper for Spotify that rips Spotify URIs to MP3 files',
    license='MIT',
    keywords="spotify ripper mp3",
    url='https://github.com/jrnewell/spotify-ripper',
    download_url = 'https://github.com/jrnewell/spotify-ripper/tarball/1.2.0',
    classifiers=[
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Sound/Audio :: Capture/Recording',
        'License :: OSI Approved :: MIT License',
        'Environment :: Console',
        "Intended Audience :: Developers",
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
    long_description=_read('README.rst'),
)
