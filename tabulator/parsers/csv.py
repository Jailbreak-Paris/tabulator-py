# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import csv
import six
from itertools import chain
from codecs import iterencode
from ..parser import Parser
from .. import exceptions
from .. import helpers
from .. import config


# Module API

class CSVParser(Parser):
    """Parser to parse CSV data format.
    """

    # Public

    options = [
        'delimiter',
        'doublequote',
        'escapechar',
        'quotechar',
        'quoting',
        'skipinitialspace',
        'lineterminator'
    ]

    def __init__(self, loader, force_parse=False, **options):

        # Make bytes
        if six.PY2:
            for key, value in options.items():
                if isinstance(value, six.string_types):
                    options[key] = str(value)

        # Set attributes
        self.__loader = loader
        self.__options = options
        self.__force_parse = force_parse
        self.__extended_rows = None
        self.__encoding = None
        self.__chars = None

    @property
    def closed(self):
        return self.__chars is None or self.__chars.closed

    def open(self, source, encoding=None):
        self.close()
        self.__chars = self.__loader.load(source, encoding=encoding)
        self.__encoding = getattr(self.__chars, 'encoding', encoding)
        if self.__encoding:
            self.__encoding.lower()
        self.reset()

    def close(self):
        if not self.closed:
            self.__chars.close()

    def reset(self):
        helpers.reset_stream(self.__chars)
        self.__extended_rows = self.__iter_extended_rows()

    @property
    def encoding(self):
        return self.__encoding

    @property
    def extended_rows(self):
        return self.__extended_rows

    # Private

    def __iter_extended_rows(self):

        # For PY2 encode/decode
        if six.PY2:
            # Reader requires utf-8 encoded stream
            bytes = iterencode(self.__chars, 'utf-8')
            sample, dialect = self.__prepare_dialect(bytes)
            items = csv.reader(chain(sample, bytes), dialect=dialect)
            for row_number, item in enumerate(items, start=1):
                values = []
                for value in item:
                    value = value.decode('utf-8')
                    values.append(value)
                yield (row_number, None, list(values))

        # For PY3 use chars
        else:
            sample, dialect = self.__prepare_dialect(self.__chars)
            items = csv.reader(chain(sample, self.__chars), dialect=dialect)
            for row_number, item in enumerate(items, start=1):
                yield (row_number, None, list(item))

    def __prepare_dialect(self, stream):

        # Get sample
        sample = []
        while True:
            try:
                sample.append(next(stream))
            except StopIteration:
                break
            if len(sample) >= config.CSV_SAMPLE_LINES:
                break

        # Get dialect
        separator = b'' if six.PY2 else ''
        delimiter = self.__options.get('delimiter')
        tested_delimiters = self.__options.get('tested_delimiters', ',\t;|')
        delimiters = tested_delimiters if delimiter is None else delimiter
        try:
            dialect = csv.Sniffer().sniff(separator.join(sample), delimiters=delimiters)
        except csv.Error as exc:
            detected_delimiter = csv.Sniffer().sniff(separator.join(sample)).delimiter
            raise exceptions.SourceError("{}: expected {} but detected {!r}".format(
                str(exc),
                "one of {!r}".format(list(delimiters)) if len(delimiters) > 1 else delimiters,
                detected_delimiter,
            ))

        if not dialect.escapechar:
            dialect.doublequote = True

        return sample, dialect
