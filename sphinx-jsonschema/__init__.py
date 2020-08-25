# -*- coding: utf-8 -*-

"""
    sphinx-jsonschema
    -----------------

    This package adds the *jsonschema* directive to Sphinx.

    Using this directory you can render JSON Schema directly
    in Sphinx.

    :copyright: Copyright 2017-2020, Leo Noordergraaf
    :licence: GPL v3, see LICENCE for details.
"""

import os.path
import json
from jsonpointer import resolve_pointer
import yaml
from collections import OrderedDict

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.utils import SystemMessagePropagation
from docutils.utils.error_reporting import SafeString
from .wide_format import WideFormat


class JsonSchema(Directive):
    optional_arguments = 1
    has_content = True
    option_spec = {'timeout': float}

    def run(self):
        try:
            schema, source = self.get_json_data()
        except SystemMessagePropagation as detail:
            return [detail.args[0]]

        format = WideFormat(self.state, self.lineno, self.state.document.settings.env.app)
        return format.transform(schema)

    def get_json_data(self):
        """
        Get JSON data from the directive content, from an external
        file, or from a URL reference.
        """
        if self.arguments:
            filename, pointer = self._splitpointer(self.arguments[0])
        else:
            filename = None
            pointer = None

        if self.content:
            if filename:
                error = self.state_machine.reporter.error(
                    '"%s" directive may not both specify an external file and'
                    ' have content.' % self.name, nodes.literal_block(
                    self.block_text, self.block_text), line=self.lineno)
                raise SystemMessagePropagation(error)
            source = self.content.source(0)
            schema = '\n'.join(self.content)
        elif filename and filename.startswith('http'):
            source = filename
            # To prevent loading on a not existing adress added timeout
            timeout = self.options.get('timeout', 30)
            if timeout < 0:
                timeout = None
            try:
                import requests
            except ImportError:
                error = self.state_machine.reporter.error(
                    '"%s" directive requires requests when loading from http.'
                    ' Try "pip install requests".' % self.name, nodes.literal_block(
                    self.block_text, self.block_text), line=self.lineno)
                raise SystemMessagePropagation(error)

            try:
                response = requests.get(source, timeout=timeout)
            except requests.exceptions.Timeout:
                error = self.state_machine.reporter.error(
                    u'"%s" directive recieved an timeout when loading from url:\n%s.'
                    % (self.name, SafeString(source)), line=self.lineno)
                raise SystemMessagePropagation(error)
             
            if response.status_code != 200:
                # When making a connection to the url a status code will be returned
                # Normally a OK (200) response would we be returned all other responses
                # an error will be raised could be seperated futher
                error = self.state_machine.reporter.error(
                    u'"%s" directive recieved an "%s" when loading from url:\n%s.'
                    % (self.name, SafeString(response.reason), SafeString(source)),
                    line=self.lineno)
                raise SystemMessagePropagation(error)

            # response content always binary converting with decode() no specific format defined
            schema = response.content.decode()
        elif filename:
            if not os.path.isabs(filename):
                # file relative to the path of the current rst file
                dname = os.path.dirname(self.state.document.current_source)
                source = os.path.join(dname, filename)
            else:
                source = filename

            self.state.document.settings.record_dependencies.add(source)
            
            try:
                with open(source) as file:
                    schema = file.read()
            except IOError as error:
                severe = self.state_machine.reporter.severe(
                    u'"%s" directive a "%s" occoured while loading file:\n%s'
                    % (self.name, SafeString(error), SafeString(source)),
                    line=self.lineno)
                raise SystemMessagePropagation(severe)
        else:
            error = self.state_machine.reporter.error(
                '"%s" directive has no content or a reference to an external file.'
                % self.name, nodes.literal_block(
                self.block_text, self.block_text), line=self.lineno)
            raise SystemMessagePropagation(error)

        try:   
            schema = self.ordered_load(schema)
        except Exception as error:
            severe = self.state_machine.reporter.severe(
                    '"%s" directive encountered a %s (%s) while parsing the data'
                     % (self.name, SafeString(type(error)), SafeString(error)),
                    nodes.literal_block(schema, schema), line=self.lineno)
            raise SystemMessagePropagation(severe)
        
        if pointer:
            try:
                schema = resolve_pointer(schema, pointer)
            except KeyError:
                error = self.state_machine.reporter.error(
                    '"%s" directive encountered a KeyError when trying to resolve the pointer'
                    ' in schema: %s' % (self.name, SafeString(pointer)),
                    nodes.literal_block(schema, schema), line=self.lineno)
                raise SystemMessagePropagation(error)

        return schema, source

    def _splitpointer(self, path):
        val = path.split('#', 1)
        if len(val) == 1:
            val.append(None)
        return val

    def ordered_load(self, text, Loader=yaml.SafeLoader, object_pairs_hook=OrderedDict):
        """Allows you to use `pyyaml` to load as OrderedDict.

        Taken from https://stackoverflow.com/a/21912744/1927102
        """
        class OrderedLoader(Loader):
            pass

        def construct_mapping(loader, node):
            loader.flatten_mapping(node)
            return object_pairs_hook(loader.construct_pairs(node))
        OrderedLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            construct_mapping)
        try:
            text = text.replace('\\(', '\\\\(')
            text = text.replace('\\)', '\\\\)')
            try:
                result = yaml.load(text, OrderedLoader)
            except yaml.scanner.ScannerError:
                # will it load as plain json?
                result = json.loads(text, object_pairs_hook=object_pairs_hook)
        except Exception as e:
            print("exception: ",e)
            self.error(e)
            result = {}
        return result


def setup(app):
    app.add_directive('jsonschema', JsonSchema)
    return {'version': '1.15'}
