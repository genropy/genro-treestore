# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for DirectoryResolver and TxtDocResolver."""

import os
import tempfile
import shutil

import pytest

from genro_treestore import TreeStore, DirectoryResolver, TxtDocResolver


class TestDirectoryResolverBasic:
    """Basic tests for DirectoryResolver."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory structure for testing."""
        base = tempfile.mkdtemp()

        # Create structure:
        # base/
        #   file1.txt
        #   file2.py
        #   subdir/
        #     nested.txt
        #   .hidden

        with open(os.path.join(base, 'file1.txt'), 'w') as f:
            f.write('content1')
        with open(os.path.join(base, 'file2.py'), 'w') as f:
            f.write('print("hello")')

        subdir = os.path.join(base, 'subdir')
        os.makedirs(subdir)
        with open(os.path.join(subdir, 'nested.txt'), 'w') as f:
            f.write('nested content')

        with open(os.path.join(base, '.hidden'), 'w') as f:
            f.write('hidden')

        yield base

        # Cleanup
        shutil.rmtree(base)

    def test_basic_directory_load(self, temp_dir):
        """DirectoryResolver loads directory contents."""
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(temp_dir, cache_time=-1))

        # Access triggers lazy load
        root_store = store['root']

        assert isinstance(root_store, TreeStore)
        assert 'file1_txt' in root_store
        assert 'file2_py' in root_store
        assert 'subdir' in root_store

    def test_hidden_files_excluded_by_default(self, temp_dir):
        """Hidden files (starting with '.') are excluded by default."""
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(temp_dir, cache_time=-1))

        root_store = store['root']

        # .hidden should not be present
        labels = list(root_store.keys())
        assert not any(l.startswith('.') or 'hidden' in l for l in labels)

    def test_hidden_files_included_with_invisible(self, temp_dir):
        """Hidden files included when invisible=True."""
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(
            temp_dir, cache_time=-1, invisible=True
        ))

        root_store = store['root']

        # .hidden should be present (dot replaced with _, no extension so trailing _)
        labels = list(root_store.keys())
        assert '_hidden_' in labels

    def test_file_attributes(self, temp_dir):
        """File metadata stored in node attributes."""
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(temp_dir, cache_time=-1))

        # Access a file
        _ = store['root']
        node = store.get_node('root.file1_txt')

        assert node.attr['file_name'] == 'file1'
        assert node.attr['file_ext'] == 'txt'
        assert node.attr['abs_path'] == os.path.join(temp_dir, 'file1.txt')
        assert node.attr['mtime'] is not None
        assert node.attr['size'] == 8  # len('content1')

    def test_subdirectory_has_resolver(self, temp_dir):
        """Subdirectories get their own DirectoryResolver."""
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(temp_dir, cache_time=-1))

        # Access root to trigger load
        _ = store['root']

        # Get subdir node
        subdir_node = store.get_node('root.subdir')

        # Should have a resolver
        assert subdir_node._resolver is not None
        assert isinstance(subdir_node._resolver, DirectoryResolver)

    def test_nested_traversal(self, temp_dir):
        """Traversal through nested directories works."""
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(temp_dir, cache_time=-1))

        # Access nested file - triggers both resolvers
        nested_node = store.get_node('root.subdir.nested_txt')

        assert nested_node.attr['file_name'] == 'nested'
        assert nested_node.attr['file_ext'] == 'txt'


class TestDirectoryResolverFiltering:
    """Tests for include/exclude filtering."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with various files."""
        base = tempfile.mkdtemp()

        # Create files with different extensions
        for name in ['file1.py', 'file2.py', 'data.json', 'readme.txt', 'test.pyc']:
            with open(os.path.join(base, name), 'w') as f:
                f.write('content')

        # Create a __pycache__ directory
        pycache = os.path.join(base, '__pycache__')
        os.makedirs(pycache)
        with open(os.path.join(pycache, 'cached.pyc'), 'w') as f:
            f.write('cached')

        yield base
        shutil.rmtree(base)

    def test_include_filter(self, temp_dir):
        """Include filter limits files to matching patterns."""
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(
            temp_dir, cache_time=-1, include='*.py'
        ))

        root_store = store['root']
        labels = list(root_store.keys())

        # Only .py files should be present (plus directories)
        assert 'file1_py' in labels
        assert 'file2_py' in labels
        assert 'data_json' not in labels
        assert 'readme_txt' not in labels

    def test_exclude_filter(self, temp_dir):
        """Exclude filter removes matching files."""
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(
            temp_dir, cache_time=-1, exclude='*.pyc,__pycache__'
        ))

        root_store = store['root']
        labels = list(root_store.keys())

        assert 'test_pyc' not in labels
        assert '__pycache__' not in labels
        assert 'file1_py' in labels  # .py files should remain

    def test_include_and_exclude(self, temp_dir):
        """Include and exclude can be combined."""
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(
            temp_dir, cache_time=-1,
            include='*.py,*.json',
            exclude='file1*'
        ))

        root_store = store['root']
        labels = list(root_store.keys())

        assert 'file1_py' not in labels  # Excluded
        assert 'file2_py' in labels
        assert 'data_json' in labels


class TestDirectoryResolverCallback:
    """Tests for callback filtering."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        base = tempfile.mkdtemp()
        for name in ['small.txt', 'large.txt']:
            with open(os.path.join(base, name), 'w') as f:
                f.write('x' * (100 if 'small' in name else 1000))
        yield base
        shutil.rmtree(base)

    def test_callback_filter(self, temp_dir):
        """Callback can filter nodes based on attributes."""
        # Only include files smaller than 500 bytes
        def size_filter(nodeattr):
            if nodeattr['size'] and nodeattr['size'] > 500:
                return False
            return None  # Include

        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(
            temp_dir, cache_time=-1, callback=size_filter
        ))

        root_store = store['root']
        labels = list(root_store.keys())

        assert 'small_txt' in labels
        assert 'large_txt' not in labels


class TestDirectoryResolverDropext:
    """Tests for dropext option."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        base = tempfile.mkdtemp()
        with open(os.path.join(base, 'file.txt'), 'w') as f:
            f.write('content')
        yield base
        shutil.rmtree(base)

    def test_dropext_false(self, temp_dir):
        """With dropext=False (default), extension is in label."""
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(temp_dir, cache_time=-1))

        root_store = store['root']
        assert 'file_txt' in root_store

    def test_dropext_true(self, temp_dir):
        """With dropext=True, extension not in label."""
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(
            temp_dir, cache_time=-1, dropext=True
        ))

        root_store = store['root']
        assert 'file' in root_store
        assert 'file_txt' not in root_store


class TestDirectoryResolverProcessors:
    """Tests for custom processors."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with a JSON file."""
        base = tempfile.mkdtemp()
        with open(os.path.join(base, 'data.json'), 'w') as f:
            f.write('{"key": "value"}')
        with open(os.path.join(base, 'skip.dat'), 'w') as f:
            f.write('skip this')
        yield base
        shutil.rmtree(base)

    def test_custom_processor(self, temp_dir):
        """Custom processor transforms file content."""
        import json

        def json_processor(path):
            with open(path) as f:
                return json.load(f)

        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(
            temp_dir, cache_time=-1,
            ext='json',
            processors={'json': json_processor}
        ))

        # Access the JSON file
        data = store['root.data_json']

        assert data == {'key': 'value'}

    def test_processor_false_skips(self, temp_dir):
        """Processor set to False skips files."""
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(
            temp_dir, cache_time=-1,
            ext='dat',
            processors={'dat': False}
        ))

        root_store = store['root']
        labels = list(root_store.keys())

        assert 'skip_dat' not in labels


class TestTxtDocResolver:
    """Tests for TxtDocResolver."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary text file."""
        fd, path = tempfile.mkstemp(suffix='.txt')
        os.write(fd, b'Hello, World!')
        os.close(fd)
        yield path
        os.unlink(path)

    def test_load_text_file(self, temp_file):
        """TxtDocResolver loads file contents as bytes."""
        from genro_treestore import TreeStoreNode

        resolver = TxtDocResolver(temp_file, cache_time=-1)
        node = TreeStoreNode('test', resolver=resolver)

        content = node.value

        assert content == b'Hello, World!'

    def test_caching(self, temp_file):
        """TxtDocResolver caches content."""
        from genro_treestore import TreeStoreNode

        resolver = TxtDocResolver(temp_file, cache_time=-1)
        node = TreeStoreNode('test', resolver=resolver)

        # First access
        content1 = node.value

        # Modify file
        with open(temp_file, 'wb') as f:
            f.write(b'Modified')

        # Second access - should return cached value
        content2 = node.value

        assert content2 == content1 == b'Hello, World!'


class TestDirectoryResolverRelocate:
    """Tests for relocate path tracking."""

    @pytest.fixture
    def temp_dir(self):
        """Create nested directory structure."""
        base = tempfile.mkdtemp()
        subdir = os.path.join(base, 'level1', 'level2')
        os.makedirs(subdir)
        with open(os.path.join(subdir, 'file.txt'), 'w') as f:
            f.write('content')
        yield base
        shutil.rmtree(base)

    def test_relocate_tracking(self, temp_dir):
        """rel_path attribute tracks relative path from root."""
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(temp_dir, cache_time=-1))

        # Navigate to nested file
        node = store.get_node('root.level1.level2.file_txt')

        # rel_path should track the relative path
        assert node.attr['rel_path'] == os.path.join('level1', 'level2', 'file.txt')


class TestDirectoryResolverEdgeCases:
    """Tests for edge cases in DirectoryResolver."""

    def test_listdir_oserror(self, tmp_path):
        """DirectoryResolver handles OSError when listing directory."""
        # Use a path that doesn't exist
        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(
            str(tmp_path / 'nonexistent'), cache_time=-1
        ))

        # Should return empty store, not raise
        root_store = store['root']
        assert len(root_store) == 0

    def test_backup_files_skipped(self, tmp_path):
        """Backup files (starting with # or ending with ~ or #) are skipped."""
        # Create backup files
        (tmp_path / '#backup#').write_text('backup1')
        (tmp_path / 'file~').write_text('backup2')
        (tmp_path / '#lock').write_text('lock')
        (tmp_path / 'normal.txt').write_text('normal')

        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(str(tmp_path), cache_time=-1))

        root_store = store['root']
        labels = list(root_store.keys())

        # Backup files should be skipped
        assert not any('#' in l or '~' in l for l in labels)
        assert 'normal_txt' in labels

    def test_stat_oserror(self, tmp_path, monkeypatch):
        """DirectoryResolver handles OSError when stat fails."""
        # Create a file
        test_file = tmp_path / 'test.txt'
        test_file.write_text('content')

        original_stat = os.stat

        def failing_stat(path):
            if 'test.txt' in str(path):
                raise OSError("Permission denied")
            return original_stat(path)

        monkeypatch.setattr(os, 'stat', failing_stat)

        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(str(tmp_path), cache_time=-1))

        root_store = store['root']
        node = store.get_node('root.test_txt')

        # File should be included but with None stats
        assert node is not None
        assert node.attr['mtime'] is None
        assert node.attr['size'] is None

    def test_numbered_caption(self, tmp_path):
        """File starting with number gets special caption formatting."""
        # Create file with numbered prefix
        (tmp_path / '01_introduction.txt').write_text('content')
        (tmp_path / '02_chapter_two.txt').write_text('content')

        store = TreeStore()
        store.set_item('root')
        store.set_resolver('root', DirectoryResolver(str(tmp_path), cache_time=-1))

        root_store = store['root']

        # Check the caption formatting
        node = store.get_node('root.01_introduction_txt')
        caption = node.attr['caption']
        # Should have !!N format for numbered files
        assert '!!' in caption or 'Introduction' in caption

    def test_directory_resolver_repr(self, tmp_path):
        """DirectoryResolver.__repr__ produces readable output."""
        resolver = DirectoryResolver(str(tmp_path), cache_time=500)
        repr_str = repr(resolver)

        assert 'DirectoryResolver' in repr_str
        assert str(tmp_path) in repr_str
        assert 'cache_time=500' in repr_str

    def test_txt_doc_resolver_repr(self, tmp_path):
        """TxtDocResolver.__repr__ produces readable output."""
        test_file = tmp_path / 'test.txt'
        test_file.write_text('content')

        resolver = TxtDocResolver(str(test_file))
        repr_str = repr(resolver)

        assert 'TxtDocResolver' in repr_str
        assert str(test_file) in repr_str
