import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='Flask-Static',
    version='1.0',
    url='http://github.com/brainfire/flask-s3',
    license='BSD',
    author='Zakaria Zajac',
    author_email='zak@brainfi.re',
    description='An extension that helps flask utilize '
                's3 for static files and uploads.',
    long_description=read('README.md'),
    packages=['flask_static'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'Flask>=0.8',
		'boto>=2.6.0'
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)