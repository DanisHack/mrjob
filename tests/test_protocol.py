# Copyright 2009-2013 Yelp and Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Make sure all of our protocols work as advertised."""
from mrjob.protocol import JSONProtocol
from mrjob.protocol import JSONValueProtocol
from mrjob.protocol import PickleProtocol
from mrjob.protocol import PickleValueProtocol
from mrjob.protocol import RawProtocol
from mrjob.protocol import RawValueProtocol
from mrjob.protocol import ReprProtocol
from mrjob.protocol import ReprValueProtocol

from tests.py2 import TestCase


class Point(object):
    """A simple class to test encoding of objects."""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return '%s.%s(%r, %r)' % (self.__module__, self.__class__.__name__,
                                  self.x, self.y)

    def __eq__(self, other):
        if not isinstance(other, Point):
            return False

        return (self.x, self.y) == (other.x, other.y)

    def __ne__(self, other):
        return not self.__eq__(other)


# keys and values that JSON protocols should encode/decode correctly
JSON_KEYS_AND_VALUES = [
    (None, None),
    (1, 2),
    ('foo', 'bar'),
    ([1, 2, 3], []),
    ({'apples': 5}, {'oranges': 20}),
    (u'Qu\xe9bec', u'Ph\u1ede'),
    ('\t', '\n'),
]

# keys and values that repr protocols should encode/decode correctly
REPR_KEYS_AND_VALUES = JSON_KEYS_AND_VALUES + [
    ((1, 2), (3, 4)),
    (b'0\xa2', b'\xe9'),
    (set([1]), set()),
]

# keys and values that pickle protocols should encode/decode properly
PICKLE_KEYS_AND_VALUES = REPR_KEYS_AND_VALUES + [
    (Point(2, 3), Point(1, 4)),
]


class ProtocolTestCase(TestCase):

    def assertRoundTripOK(self, protocol, key, value):
        """Assert that we can encode and decode the given key and value,
        and get the same key and value we started with."""
        self.assertEqual((key, value),
                         protocol.read(protocol.write(key, value)))

    def assertRoundTripWithTrailingTabOK(self, protocol, key, value):
        """Assert that we can encode the given key and value, add a
        trailing tab (which Hadoop sometimes does), and decode it
        to get the same key and value we started with."""
        self.assertEqual((key, value),
                         protocol.read(protocol.write(key, value) + b'\t'))

    def assertCantEncode(self, protocol, key, value):
        self.assertRaises(Exception, protocol.write, key, value)

    def assertCantDecode(self, protocol, data):
        self.assertRaises(Exception, protocol.read, data)


class JSONProtocolTestCase(ProtocolTestCase):

    def test_round_trip(self):
        for k, v in JSON_KEYS_AND_VALUES:
            self.assertRoundTripOK(JSONProtocol(), k, v)

    def test_round_trip_with_trailing_tab(self):
        for k, v in JSON_KEYS_AND_VALUES:
            self.assertRoundTripWithTrailingTabOK(JSONProtocol(), k, v)

    def test_uses_json_format(self):
        KEY = ['a', 1]
        VALUE = {'foo': 'bar'}
        ENCODED = b'["a", 1]\t{"foo": "bar"}'

        self.assertEqual((KEY, VALUE), JSONProtocol().read(ENCODED))
        self.assertEqual(ENCODED, JSONProtocol().write(KEY, VALUE))

    def test_tuples_become_lists(self):
        # JSON should convert tuples into lists
        self.assertEqual(
            ([1, 2], [3, 4]),
            JSONProtocol().read(JSONProtocol().write((1, 2), (3, 4))))

    def test_numerical_keys_become_strs(self):
        # JSON should convert numbers to strings when they are dict keys
        self.assertEqual(
            ({'1': 2}, {'3': 4}),
            JSONProtocol().read(JSONProtocol().write({1: 2}, {3: 4})))

    def test_bad_data(self):
        self.assertCantDecode(JSONProtocol(), b'{@#$@#!^&*$%^')

    def test_bad_keys_and_values(self):
        # dictionaries have to have strings as keys
        self.assertCantEncode(JSONProtocol(), {(1, 2): 3}, None)

        # only unicodes (or bytes in utf-8) are allowed
        self.assertCantEncode(JSONProtocol(), b'0\xa2', b'\xe9')

        # sets don't exist in JSON
        self.assertCantEncode(JSONProtocol(), set([1]), set())

        # Point class has no representation in JSON
        self.assertCantEncode(JSONProtocol(), Point(2, 3), Point(1, 4))


class JSONValueProtocolTestCase(ProtocolTestCase):

    def test_round_trip(self):
        for _, v in JSON_KEYS_AND_VALUES:
            self.assertRoundTripOK(JSONValueProtocol(), None, v)

    def test_round_trip_with_trailing_tab(self):
        for _, v in JSON_KEYS_AND_VALUES:
            self.assertRoundTripWithTrailingTabOK(JSONValueProtocol(), None, v)

    def test_uses_json_format(self):
        VALUE = {'foo': 'bar'}
        ENCODED = b'{"foo": "bar"}'

        self.assertEqual((None, VALUE), JSONValueProtocol().read(ENCODED))
        self.assertEqual(ENCODED, JSONValueProtocol().write(None, VALUE))

    def test_tuples_become_lists(self):
        # JSON should convert tuples into lists
        self.assertEqual(
            (None, [3, 4]),
            JSONValueProtocol().read(JSONValueProtocol().write(None, (3, 4))))

    def test_numerical_keys_become_strs(self):
        # JSON should convert numbers to strings when they are dict keys
        self.assertEqual(
            (None, {'3': 4}),
            JSONValueProtocol().read(JSONValueProtocol().write(None, {3: 4})))

    def test_bad_data(self):
        self.assertCantDecode(JSONValueProtocol(), b'{@#$@#!^&*$%^')

    def test_bad_keys_and_values(self):
        # dictionaries have to have strings as keys
        self.assertCantEncode(JSONValueProtocol(), None, {(1, 2): 3})

        # only unicodes (or bytes in utf-8) are allowed
        self.assertCantEncode(JSONValueProtocol(), None, b'\xe9')

        # sets don't exist in JSON
        self.assertCantEncode(JSONValueProtocol(), None, set())

        # Point class has no representation in JSON
        self.assertCantEncode(JSONValueProtocol(), None, Point(1, 4))


class PickleProtocolTestCase(ProtocolTestCase):

    def test_round_trip(self):
        for k, v in PICKLE_KEYS_AND_VALUES:
            self.assertRoundTripOK(PickleProtocol(), k, v)

    def test_round_trip_with_trailing_tab(self):
        for k, v in PICKLE_KEYS_AND_VALUES:
            self.assertRoundTripWithTrailingTabOK(PickleProtocol(), k, v)

    def test_bad_data(self):
        self.assertCantDecode(PickleProtocol(), b'{@#$@#!^&*$%^')

    # no tests of what encoded data looks like; pickle is an opaque protocol


class PickleValueProtocolTestCase(ProtocolTestCase):

    def test_round_trip(self):
        for _, v in PICKLE_KEYS_AND_VALUES:
            self.assertRoundTripOK(PickleValueProtocol(), None, v)

    def test_round_trip_with_trailing_tab(self):
        for _, v in PICKLE_KEYS_AND_VALUES:
            self.assertRoundTripWithTrailingTabOK(
                PickleValueProtocol(), None, v)

    def test_bad_data(self):
        self.assertCantDecode(PickleValueProtocol(), b'{@#$@#!^&*$%^')

    # no tests of what encoded data looks like; pickle is an opaque protocol


class RawValueProtocolTestCase(ProtocolTestCase):

    def test_dumps_keys(self):
        self.assertEqual(RawValueProtocol().write(b'foo', b'bar'), b'bar')

    def test_reads_raw_line(self):
        self.assertEqual(RawValueProtocol().read(b'foobar'), (None, b'foobar'))

    def test_bytestrings(self):
        self.assertRoundTripOK(RawValueProtocol(), None, b'\xe90\c1a')

    def test_no_strip(self):
        self.assertEqual(RawValueProtocol().read(b'foo\t \n\n'),
                         (None, b'foo\t \n\n'))


class RawProtocolTestCase(ProtocolTestCase):

    def test_round_trip(self):
        self.assertRoundTripOK(RawProtocol(), b'foo', b'bar')
        self.assertRoundTripOK(RawProtocol(), b'foo', None)
        self.assertRoundTripOK(RawProtocol(), b'foo', b'')
        self.assertRoundTripOK(RawProtocol(), b'caf\xe9', b'\xe90\c1a')

    def test_no_tabs(self):
        self.assertEqual(RawProtocol().write(b'foo', None), b'foo')
        self.assertEqual(RawProtocol().write(None, b'foo'), b'foo')
        self.assertEqual(RawProtocol().read(b'foo'), (b'foo', None))

        self.assertEqual(RawProtocol().write(b'', None), b'')
        self.assertEqual(RawProtocol().write(None, None), b'')
        self.assertEqual(RawProtocol().write(None, b''), b'')
        self.assertEqual(RawProtocol().read(b''), (b'', None))

    def test_extra_tabs(self):
        self.assertEqual(RawProtocol().write(b'foo', b'bar\tbaz'),
                         b'foo\tbar\tbaz')
        self.assertEqual(RawProtocol().write(b'foo\tbar', b'baz'),
                         b'foo\tbar\tbaz')
        self.assertEqual(RawProtocol().read(b'foo\tbar\tbaz'),
                         (b'foo', b'bar\tbaz'))

    def test_no_strip(self):
        self.assertEqual(RawProtocol().read(b'foo\t \n\n'),
                         (b'foo', b' \n\n'))


class ReprProtocolTestCase(ProtocolTestCase):

    def test_round_trip(self):
        for k, v in REPR_KEYS_AND_VALUES:
            self.assertRoundTripOK(ReprProtocol(), k, v)

    def test_round_trip_with_trailing_tab(self):
        for k, v in REPR_KEYS_AND_VALUES:
            self.assertRoundTripWithTrailingTabOK(ReprProtocol(), k, v)

    def test_uses_repr_format(self):
        KEY = ['a', 1]
        VALUE = {'foo': {'bar': 3}, 'baz': None}
        ENCODED = ('%r\t%r' % (KEY, VALUE)).encode('ascii')

        self.assertEqual((KEY, VALUE), ReprProtocol().read(ENCODED))
        self.assertEqual(ENCODED, ReprProtocol().write(KEY, VALUE))

    def test_bad_data(self):
        self.assertCantDecode(ReprProtocol(), b'{@#$@#!^&*$%^')

    def test_can_encode_point_but_not_decode(self):
        points_encoded = ReprProtocol().write(Point(2, 3), Point(1, 4))
        self.assertCantDecode(ReprProtocol(), points_encoded)


class ReprValueProtocolTestCase(ProtocolTestCase):

    def test_round_trip(self):
        for _, v in REPR_KEYS_AND_VALUES:
            self.assertRoundTripOK(ReprValueProtocol(), None, v)

    def test_round_trip_with_trailing_tab(self):
        for _, v in REPR_KEYS_AND_VALUES:
            self.assertRoundTripWithTrailingTabOK(ReprValueProtocol(), None, v)

    def test_uses_repr_format(self):
        VALUE = {'foo': {'bar': 3}, 'baz': None, 'quz': ['a', 1]}

        self.assertEqual((None, VALUE), ReprValueProtocol().read(repr(VALUE)))
        self.assertEqual(repr(VALUE).encode('ascii'),
                         ReprValueProtocol().write(None, VALUE))

    def test_bad_data(self):
        self.assertCantDecode(ReprValueProtocol(), b'{@#$@#!^&*$%^')

    def test_can_encode_point_but_not_decode(self):
        points_encoded = ReprValueProtocol().write(None, Point(1, 4))
        self.assertCantDecode(ReprValueProtocol(), points_encoded)
