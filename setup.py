#!/usr/bin/env python
# coding=utf-8

from setuptools import setup, find_packages

setup(
    name='spotify-ripper',
    version='1.0.0',
    packages=find_packages(exclude=["tests"]),
    scripts=['spotify_ripper/ripper.py'],
    include_package_data=True,
    zip_safe=False,

     # Executable
    entry_points={
        'console_scripts': [
            'spotify-ripper = ripper:main',
        ],
    },

    # Additional data
    package_data={
        '': ['README.rst', 'LICENCE']
    },

    # Requirements
    install_requires=[
        'pyspotify==2.0.0b4',
        'colorama==0.3.3',
        'eyeD3==0.7.5',
    ],

    # Metadata
    author='James Newell',
    description='a small ripper for Spotify that rips Spotify URIs to MP3 files',
    license='MIT',
    keywords="spotify ripper mp3",
    url='https://github.com/jrnewell/spotify-ripper',
    classifiers=[
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Sound/Audio :: Capture/Recording',
        'License :: OSI Approved :: MIT License',
        'Environment :: Console',
        "Intended Audience :: Developers",
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
    long_description=open('README.md').read()
)
