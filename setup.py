from setuptools import setup, find_packages

__author__ = 'wddd'
__version__ = '0.3.0'

setup(
    name='weibo_api',
    version=__version__,
    author=__author__,
    license='MIT',
    url='https://github.com/wdwind/weibo_api/tree/master',
    install_requires=['cookiejar', 'mxnet>=1.3.1,<1.10.0', 'pillow', 'requests', 'requests_toolbelt', 'rsa'],
    test_requires=[],
    include_package_data=True,
    keywords='Weibo api',
    description='An api for posting weibo (text, image, and video).',
    packages=find_packages(exclude=('tests',)),
    package_data={'': ['model/*.params', 'model/*.json', 'model/*.pkl']},
    classifiers=[
        'Development Status :: Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3.7',
    ],
)
