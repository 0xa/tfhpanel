import os

from setuptools import setup, find_packages

requires = [
    'pyramid',
    'SQLAlchemy',
    'transaction',
    'mako',
    'pyramid_mako',
    'pyramid_tm',
    'pyramid_beaker',
    'pgpdump',
    'waitress',
    'alembic',
    'Babel',
    ]

setup(name='tfhpanel',
      version='0.0',
      description='tfhpanel',
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='tfhpanel',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = tfhpanel:main
      """,
      message_extractors = {'tfhpanel': [
        ('**.py', 'python', None),
        ('templates/**.html', 'mako', None),
        ('templates/**.mako', 'mako', None),
        ('static/**', 'ignore', None)]},
      )

