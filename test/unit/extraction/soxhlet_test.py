import os
import unittest as ut
from unittest import mock
from tesliper.extraction import soxhlet as sx


class TestSoxhlet(ut.TestCase):

    def setUp(self):
        with mock.patch(
                'tesliper.extraction.soxhlet.os.listdir',
                return_value='a.out b.out b.gjf'.split(' ')
        ) as lsdir:
            self.sx = sx.Soxhlet()
            self.lsdir = lsdir

    def test_path_default(self):
        self.assertEqual(self.sx.path, os.getcwd())

    @mock.patch(
        'tesliper.extraction.soxhlet.os.path.isdir', return_values=True
    )
    def test_path_non_existing_path(self, isdir):
        with self.assertRaises(FileNotFoundError):
            self.sx.path = '\\path\\doesnt\\exist'
        isdir.assert_called()

    @mock.patch(
        'tesliper.extraction.soxhlet.os.listdir',
        return_value='new.out files.out'.split(' ')
    )
    @mock.patch(
        'tesliper.extraction.soxhlet.os.path.isdir', return_values=True
    )
    def test_path_ok(self, isdir, listdir):
        self.sx.path = '\\path\\is\\ok'
        self.assertEqual('\\path\\is\\ok', self.sx.path)
        isdir.assert_called()
        listdir.assert_called_with('\\path\\is\\ok')
        self.assertSequenceEqual('new.out files.out'.split(' '), self.sx.files)

    def test_filter_files_no_extension(self):
        self.assertRaises(ValueError, self.sx.filter_files)

    def test_filter_files(self):
        self.assertSequenceEqual(
            'a.out b.out'.split(' '), self.sx.filter_files('.out')
        )
        self.assertSequenceEqual(['b.gjf'], self.sx.filter_files('.gjf'))

    def test_filter_files_empty(self):
        self.assertSequenceEqual([], self.sx.filter_files('.log'))

    def test_guess_extension(self):
        self.assertEqual('.out', self.sx.guess_extension())
        self.sx.files = 'a.log b.log b.gjf'.split(' ')
        self.assertEqual('.log', self.sx.guess_extension())

    def test_guess_extension_mixed(self):
        self.sx.files = 'a.out b.log b.gjf'.split(' ')
        self.assertRaises(ValueError, self.sx.guess_extension)

    def test_guess_extension_missing(self):
        self.sx.files = 'b.gjf'.split(' ')
        self.assertRaises(TypeError, self.sx.guess_extension)

    def test_output_files(self):
        self.sx.guess_extension = mock.Mock(return_value='.out')
        self.sx.filter_files = mock.Mock(return_value=['a.out', 'b.out'])
        self.assertSequenceEqual(['a.out', 'b.out'], self.sx.output_files)
        self.sx.guess_extension.assert_called()
        self.sx.filter_files.assert_called_with('.out')

    def test_files(self):
        self.assertSequenceEqual('a.out b.out b.gjf'.split(' '), self.sx.files)

    @mock.patch('tesliper.extraction.soxhlet.open', mock.mock_open())
    @mock.patch(
        'tesliper.extraction.soxhlet.os.listdir',
        return_value='a.out b.out b.gjf'.split(' ')
    )
    @mock.patch(
        'tesliper.extraction.soxhlet.Soxhlet.output_files',
        new_callable=mock.PropertyMock
    )
    def test_extract_iter(self, output, lsdir):
        sox = sx.Soxhlet()
        parser = mock.Mock(parse=mock.Mock(return_value={}))
        sox.parser = parser
        output.return_value = ['a.out', 'b.out']
        out = dict(sox.extract_iter())
        self.assertDictEqual({'a.out': {}, 'b.out': {}}, out)
        output.assert_called()
        parser.parse.assert_called()
        self.assertEqual(2, parser.parse.call_count)
