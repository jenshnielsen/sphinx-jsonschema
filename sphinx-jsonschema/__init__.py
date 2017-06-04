# -*- coding: utf-8 -*-

"""
    sphinx-jsonschema
    -----------------
    
    This package adds the *jsonschema* directive to Sphinx.
    
    Using this directory you can render JSON Schema directly
    in Sphinx.
    
    :copyright: Copyright 2017, Leo Noordergraaf
    :licence: GPL v3, see LICENCE for details.
"""

import json
from docutils.parsers.rst import Directive
from .wide_format import WideFormat

# TODO find out if app is accessible from Directive
_glob_app = None

class JsonSchema(Directive):
    optional_arguments = 1
    has_content = True
    option_spec = {'display_if': str}
    
    def __init__(self, directive, arguments, options, content, lineno, content_offset, block_text, state, state_machine):
        """Constructor
        
        Finds out where the schema is located and fetches it.
        """
        assert directive == 'jsonschema'
        
        # state_machine.document.source_file => filename of current document
        
        self.options = options
        self.state = state
        self.lineno = lineno
        self.statemachine = state_machine
        if len(arguments) == 1:
            self._load_external(arguments[0])
        else:
            self._load_internal(content)

    def run(self):
        """Print the schema
        
        Currently only the WideFormat layout is supported.
        
        The schema is transformed into a table specification and
        the Sphinx table builder is used to render it.
        """
        if 'display_if' in self.options:
            if '$$display' not in self.schema or self.options['display_if'] != self.schema['$$display']:
                return []
        format = WideFormat()
        return format.transform(self.schema, self.state, self.lineno, _glob_app)

    def _load_external(self, file_or_url):
        """Load external schema
        
        Loads the schema from a web URL or a local file, depending
        on whether the resource name starts with 'http' or not.
        
        The imported schema is stored in the `schema` property.
        """
        if file_or_url.startswith('http'):
            try:
                import requests
            except ImportError:
                raise Exception("JSONSCHEMA loading from http requires requests. Try 'pip install requests'")
            text = requests.get(file_or_url)
            self.schema = json.loads(text.content)
        else:
            with open(file_or_url) as file:
                self.schema = json.load(file)

    def _load_internal(self, text):
        """Load embedded schema
        
        Loads the schema from the block following the directive.
        
        The imported schema is stored in the `schema` property.
        """
        if text is None or len(text) == 0:
            raise Exception("JSONSCHEMA requires either filename, http url or inline content")
        self.schema = json.loads('\n'.join(text))

def setup(app):
    """Bind into Sphinx
    
    Add the directive to Sphinx.
    """
    # app.srcdir => source directory
    global _glob_app
    _glob_app = app
    app.add_directive('jsonschema', JsonSchema)
    return {'version': '1.0'}
