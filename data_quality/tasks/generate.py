# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import io
import json
import importlib
from data_quality import generators, utilities, compat
from .base_task import Task
from .check_datapackage import DataPackageChecker


class GeneratorManager(Task):

    """A Task runner that manages dataset generators (ex: CkanGenerator)."""

    def __init__(self, config):
        super(GeneratorManager, self).__init__(config)
        datapackage_check = DataPackageChecker(self.config)
        datapackage_check.run()

    def run(self, generator_name, endpoint, generator_path, file_types, simulate=False):
        """Delegate the generation processes to the chosen generator
        Args:
            generator_name: Name of the generator (ex: ckan)
            endpoint: Url where the generator should get the data from
            generator_path: Path to the custom generator class, if used
            file_types: List of file types that should be included in sources
        """

        if generators._built_in_generators.get(generator_name, None):
            inflexible_resources = ['source_file', 'publisher_file']
            datapackage_check = DataPackageChecker(self.config, inflexible_resources)
            try:
                datapackage_check.run()
            except ValueError as e:
                msg = ('Looks like you have a custom schema for "{0}". Generator '
                       '"{1}" only works with the default schema. Please use a '
                       'custom generator or match your schema to the default one.'
                      ).format(e[1], generator_name)
                raise ValueError(msg)

            generator_class = generators._built_in_generators[generator_name]
        else:
            try:
                _module, _class = generator_path.rsplit('.', 1)
                generator_class = getattr(importlib.import_module(_module), _class)
            except ValueError:
                raise ValueError(('The path you provided for the generator class is '
                                  'not valid. Should be of type `mymodule.MyGenerator`'))
        generator = generator_class(endpoint, self.datapackage)

        if simulate:
            return generator

        generator.generate_sources(self.source_file, file_types=file_types)
        generator.generate_publishers(self.publisher_file)

    def update_datapackage_sources(self):
        """Update the 'sources' property of datapackage with the new sources"""

        datapackage_check = DataPackageChecker(self.config)
        required_resources = [self.source_file, self.publisher_file]
        datapackage_check.check_database_completeness(required_resources)
        datapackage_check.run()
        self.datapackage.descriptor['sources'] = []
        datapkg_path = os.path.join(self.datapackage.base_path, 'datapackage.json')

        with compat.UnicodeDictReader(self.source_file) as sources_file:
            for source in sources_file:
                src_info = {'name': source['title'], 'web': source[self.data_key]}
                self.datapackage.descriptor['sources'].append(src_info)

        with io.open(datapkg_path, mode='w+', encoding='utf-8') as datapkg_file:
            new_datapkg = json.dumps(self.datapackage.to_dict(), indent=4,
                                     sort_keys=True)
            datapkg_file.write(compat.str(new_datapkg))
