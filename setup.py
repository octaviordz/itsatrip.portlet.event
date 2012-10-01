from setuptools import setup, find_packages
import os

version = '0.1.0-version3'

setup(name='example.portlet.foo',
      version=version,
      description="An example portlet, just done for my blog article",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        ],
      keywords='plone portlet example blog',
      author='keul',
      author_email='luca@keul.it',
      url='http://svn.plone.org/svn/collective/example.portlet.foo',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['example', 'example.portlet'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
      ],
      entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
