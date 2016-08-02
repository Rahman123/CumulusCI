import os
import shutil
import tempfile
import unittest

import mock
import nose
import yaml

from core.config import BaseConfig
from core.config import YamlGlobalConfig
from core.config import YamlProjectConfig
from core.exceptions import NotInProject
from core.exceptions import ProjectConfigNotFound

__location__ = os.path.dirname(os.path.realpath(__file__))


class TestBaseConfig(unittest.TestCase):

    def test_getattr_toplevel_key(self):
        config = BaseConfig()
        config.config = {'foo': 'bar'}
        self.assertEquals(config.foo, 'bar')

    def test_getattr_toplevel_key_missing(self):
        config = BaseConfig()
        config.config = {}
        self.assertEquals(config.foo, None)

    def test_getattr_child_key(self):
        config = BaseConfig()
        config.config = {'foo': {'bar': 'baz'}}
        self.assertEquals(config.foo__bar, 'baz')

    def test_getattr_child_parent_key_missing(self):
        config = BaseConfig()
        config.config = {}
        self.assertEquals(config.foo__bar, None)

    def test_getattr_child_key_missing(self):
        config = BaseConfig()
        config.config = {'foo': {}}
        self.assertEquals(config.foo__bar, None)

    def test_getattr_default_toplevel(self):
        config = BaseConfig()
        config.config = {'foo': 'bar'}
        config.defaults = {'foo': 'default'}
        self.assertEquals(config.foo, 'bar')

    def test_getattr_default_toplevel_missing_default(self):
        config = BaseConfig()
        config.config = {'foo': 'bar'}
        config.defaults = {}
        self.assertEquals(config.foo, 'bar')

    def test_getattr_default_toplevel_missing_config(self):
        config = BaseConfig()
        config.config = {}
        config.defaults = {'foo': 'default'}
        self.assertEquals(config.foo, 'default')

    def test_getattr_default_child(self):
        config = BaseConfig()
        config.config = {'foo': {'bar': 'baz'}}
        config.defaults = {'foo__bar': 'default'}
        self.assertEquals(config.foo__bar, 'baz')

    def test_getattr_default_child_missing_default(self):
        config = BaseConfig()
        config.config = {'foo': {'bar': 'baz'}}
        config.defaults = {}
        self.assertEquals(config.foo__bar, 'baz')

    def test_getattr_default_child_missing_config(self):
        config = BaseConfig()
        config.config = {}
        config.defaults = {'foo__bar': 'default'}
        self.assertEquals(config.foo__bar, 'default')

    def test_getattr_empty_search_path(self):
        config = BaseConfig()
        config.search_path = []
        self.assertEquals(config.foo, None)

    def test_getattr_search_path_no_match(self):
        config = BaseConfig()
        config.search_path = ['_first', '_middle', '_last']
        config._first = {}
        config._middle = {}
        config._last = {}
        self.assertEquals(config.foo, None)

    def test_getattr_search_path_match_first(self):
        config = BaseConfig()
        config.search_path = ['_first', '_middle', '_last']
        config._first = {'foo': 'bar'}
        config._middle = {}
        config._last = {}
        self.assertEquals(config.foo, 'bar')

    def test_getattr_search_path_match_middle(self):
        config = BaseConfig()
        config.search_path = ['_first', '_middle', '_last']
        config._first = {}
        config._middle = {'foo': 'bar'}
        config._last = {}
        self.assertEquals(config.foo, 'bar')

    def test_getattr_search_path_match_last(self):
        config = BaseConfig()
        config.search_path = ['_first', '_middle', '_last']
        config._first = {}
        config._middle = {}
        config._last = {'foo': 'bar'}
        self.assertEquals(config.foo, 'bar')


class TestYamlGlobalConfig(unittest.TestCase):

    def test_load_global_config(self):
        config = YamlGlobalConfig()
        f_expected_config = open(__location__ + '/../../cumulusci.yml', 'r')
        expected_config = yaml.load(f_expected_config)
        self.assertEquals(config.config, expected_config)


@mock.patch('os.path.expanduser')
class TestYamlProjectConfig(unittest.TestCase):

    def _create_git_config(self):
        filename = os.path.join(self.tempdir_project, '.git', 'config')
        content = (
            '[remote "origin"]\n' +
            '  url = git@github.com:TestOwner/{}'.format(self.project_name)
        )
        self._write_file(filename, content)

    def _create_project_config(self):
        filename = os.path.join(
            self.tempdir_project,
            YamlProjectConfig.config_filename,
        )
        content = (
            'project:\n' +
            '    name: TestProject\n' +
            '    namespace: testproject\n'
        )
        self._write_file(filename, content)

    def _create_project_config_local(self, content):
        project_local_dir = os.path.join(
            self.tempdir_home,
            '.cumulusci',
            self.project_name,
        )
        os.makedirs(project_local_dir)
        filename = os.path.join(project_local_dir,
                                YamlProjectConfig.config_filename)
        self._write_file(filename, content)

    def _write_file(self, filename, content):
        f = open(filename, 'w')
        f.write(content)
        f.close()

    def setUp(self):
        self.tempdir_home = tempfile.mkdtemp()
        self.tempdir_project = tempfile.mkdtemp()
        self.project_name = 'TestRepo'

    def tearDown(self):
        shutil.rmtree(self.tempdir_home)
        shutil.rmtree(self.tempdir_project)

    @nose.tools.raises(NotInProject)
    def test_load_project_config_not_repo(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)

    @nose.tools.raises(ProjectConfigNotFound)
    def test_load_project_config_no_config(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, '.git'))
        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)

    def test_load_project_config_empty_config(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, '.git'))
        self._create_git_config()
        # create empty project config file
        filename = os.path.join(self.tempdir_project,
                                YamlProjectConfig.config_filename)
        content = ''
        self._write_file(filename, content)

        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)
        self.assertEquals(config.config_project, {})

    def test_load_project_config_valid_config(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, '.git'))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)
        self.assertEquals(config.project__name, 'TestProject')
        self.assertEquals(config.project__namespace, 'testproject')

    def test_load_project_config_local(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, '.git'))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        # create local project config file
        content = (
            'project:\n' +
            '    name: TestProject2\n'
        )
        self._create_project_config_local(content)

        os.chdir(self.tempdir_project)
        global_config = YamlGlobalConfig()
        config = YamlProjectConfig(global_config)
        self.assertNotEqual(config.config_project_local, {})
        self.assertEqual(config.project__name, 'TestProject2')
        self.assertEqual(config.project__namespace, 'testproject')
