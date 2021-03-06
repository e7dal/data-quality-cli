# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import csv
from os import path
import requests
import jsontableschema
from data_quality import compat, utilities
from .base import BaseGenerator

class CkanGenerator(BaseGenerator):
    """This class generates a csv database from a CKAN instance located at the given url"""

    def __init__(self, url=None, datapackage=None):
        """Create an instance if the source url is given.

        Args:
            url: the base url for the CKAN instance
        """

        super(CkanGenerator, self).__init__(url, datapackage)
        self.default_publisher = None

    def generate_sources(self, sources_filepath, file_types=['csv', 'excel']):
        """Generates sources_file from the url"""

        file_types = [ftype.lower() for ftype in file_types]
        results = self.get_sources()
        sources = []
        source_resource = utilities.get_datapackage_resource(sources_filepath,
                                                             self.datapackage)
        source_schema = jsontableschema.model.SchemaModel(source_resource.descriptor['schema'])
        for result in results:
            sources += self.extract_sources(result, file_types)

        with compat.UnicodeWriter(sources_filepath,
                                  quoting=csv.QUOTE_MINIMAL) as sfile:
            sfile.writerow(source_schema.headers)
            for source in sources:
                try:
                    values = [compat.str(source[key]) for key in source_schema.headers]
                    sfile.writerow(list(source_schema.convert_row(*values)))
                except jsontableschema.exceptions.MultipleInvalid as e:
                    for error in e.errors:
                        raise error

    def get_sources(self):
        """Get all sources from CKAN API as a list"""

        extension = 'api/3/action/package_search'
        full_url = compat.urljoin(self.base_url, extension)
        response = requests.get(full_url)
        response.raise_for_status()
        data = response.json()
        count = data['result']['count']
        all_packages = []
        all_sources = []
        for start in range(0, count, 500):
            payload = {'rows': 500, 'start': start}
            response = requests.get(full_url, params=payload)
            data = response.json()
            all_packages += [result['id'] for result in  data['result']['results']]

        for package_id in all_packages:
            ext = 'api/3/action/package_show'
            full_package_url = compat.urljoin(self.base_url, ext)
            package_payload = {'use_default_schema': True, 'id': package_id}
            response = requests.get(full_package_url, params=package_payload)
            data = response.json()
            all_sources.append(data['result'])
        return all_sources

    def extract_sources(self, datum, file_types):
        """Extract all sources for one result"""

        resources = []
        for resource in datum.get('resources', {}):
            new_resource = {}
            new_resource['data'] = resource['url']
            ext = path.splitext(new_resource['data'])[1][1:].lower()
            new_resource['format'] = 'excel' if ext in ['xls', 'xlsx'] else ext
            file_types = ['excel' if ext in ['xls', 'xlsx'] else ext for ext in file_types]
            file_types.append('')
            if new_resource['format'] in file_types:
                publisher = datum.get('organization', None)
                if publisher:
                    new_resource['publisher_id'] = publisher.get('name')
                else:
                    self.default_publisher = {'name': 'no_organization',
                                              'display_name': 'No Organization'}
                    new_resource['publisher_id'] = self.default_publisher['name']
                new_resource['id'] = resource['id']
                new_resource['created_at'] = resource['created']
                title = datum.get('title', '')
                name = resource.get('name', '')
                new_resource['title'] = ' / '.join(val for val in [title, name] if val)
                resources.append(new_resource)
        return resources

    def generate_publishers(self, publishers_filepath):
        """Generates publisher_file from the url"""

        results = self.get_publishers()
        if self.default_publisher:
            results.append(self.default_publisher)
        pub_resource = utilities.get_datapackage_resource(publishers_filepath,
                                                          self.datapackage)
        pub_schema = jsontableschema.model.SchemaModel(pub_resource.descriptor['schema'])

        with compat.UnicodeWriter(publishers_filepath,
                                  quoting=csv.QUOTE_MINIMAL) as pfile:
            pfile.writerow(pub_schema.headers)
            for result in results:
                result = self.extract_publisher(result)
                try:
                    values = [result[key] for key in pub_schema.headers]
                    pfile.writerow(list(pub_schema.convert_row(*values)))
                except jsontableschema.exceptions.MultipleInvalid as e:
                    for error in e.errors:
                        raise error

    def get_publishers(self):
        """Retrieves the publishers from CKAN API as a list"""

        extension = "api/3/action/organization_list"
        payload = {'all_fields':True,
                   'include_groups': True,
                   'include_extras':True
                  }
        full_url = compat.urljoin(self.base_url, extension)
        response = requests.get(full_url, params=payload)
        publishers = response.json()['result']
        return publishers

    def extract_publisher(self, result):
        """Converts `result` into dict with standard compliant field names"""

        publisher = {}
        publisher['id'] = result.get('name', '')
        publisher['title'] = result.get('display_name', '')
        for extra in result.get('extras', []):
            key = extra.get('key')
            if key == 'contact-email':
                publisher['email'] = extra.get('value')
            if key == 'contact-name':
                publisher['contact'] = extra.get('value')
            if key == 'category':
                publisher['type'] = extra.get('value')
        return publisher
