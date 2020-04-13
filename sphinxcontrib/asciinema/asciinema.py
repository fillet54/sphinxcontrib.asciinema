import hashlib
import os
import posixpath

from docutils import nodes
from docutils.parsers.rst import directives, Directive
from sphinx.util.fileutil import copy_asset
from sphinx.util.docutils import SphinxDirective
from sphinx.util.osutil import relative_uri
from sphinx import addnodes

from sphinxcontrib.confluencebuilder.state import ConfluenceState

from docutils.statemachine import ViewList
from docutils.parsers.rst.directives.misc import Include

def copy_asset_files(app, exc):
    asset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             '_static')
    if exc is None:  # build succeeded
        for file in os.listdir(asset_dir):
            copy_asset(os.path.join(asset_dir, file),
                       os.path.join(app.outdir, '_static'))


class Asciinema(nodes.container):
    cast_file = None
    cast_id = None


def visit(self, node):
    if node.cast_file is not None:
        template = '<asciinema-player {options} src="{src}"></asciinema-player>'
        option_template = '{}="{}" '
        src = node.cast_file
    else:
        template = '<script id="asciicast-{src}" {options} src="https://asciinema.org/a/{src}.js" async></script>'
        option_template = 'data-{}="{}" '
        src = node.cast_id
    options = ''
    for n, v in node.options.items():
        options += option_template.format(n, v)
    tag = (template.format(options=options, src=src))
    self.body.append(tag)


def depart(self, node):
    pass


def conf_visit(self, node):

    # This EXPECTS an attachment. Currently does not handle absolute URI
    file_key, hosting_docname = self.assets.fetch(node.children[0])
    hosting_doctitle = ConfluenceState.title(hosting_docname)
    hosting_doctitle = self._escape_sf(hosting_doctitle)

    self.body.append(self._start_ac_macro(node, 'asciicinema'))
    self.body.append(self._build_ac_parameter(node, "CastFile", file_key))
    self.body.append(self._build_ac_parameter(node, "PageTitle", hosting_doctitle))
    self.body.append(self._end_ac_macro(node))

    # Override whatever confluencebuilder does with a download node
    # We just want download node to appear in tree so file gets attached
    # to a page
    self.context.append(self.body)
    self.body = []

def conf_depart(self, node):
    self.body = self.context.pop()

class ASCIINemaDirective(SphinxDirective):

    name = 'asciinema'
    node_class = Asciinema

    has_content = False
    final_argument_whitespace = False
    option_spec = {
        'cols': directives.positive_int,
        'rows': directives.positive_int,
        'autoplay': directives.unchanged,
        'preload': directives.unchanged,
        'loop': directives.unchanged,
        'start-at': directives.unchanged,
        'speed': directives.unchanged,
        'idle-time-limit': directives.unchanged,
        'poster': directives.unchanged,
        'font-size': directives.unchanged,
        'size': directives.unchanged,
        'theme': directives.unchanged,
        'title': directives.unchanged,
        't': directives.unchanged,
        'author': directives.unchanged,
        'author-url': directives.unchanged,
        'author-img-url': directives.unchanged
    }
    required_arguments = 1
    optional_arguments = len(option_spec)

    def run(self):
        node = self.node_class()
        arg = self.arguments[0]
        if self.is_file(arg):
            node.cast_file = self.add_file(arg)
        else:
            node.cast_id = arg
        node.options = self.env.config['sphinxcontrib_asciinema_defaults']
        node.options.update(self.options)

        # Only add download node for confluence
        if self.env.app.builder.name == 'confluence':
            rst = ViewList()
            rst.append(":download:`{}`".format(arg), "asciinema.py", 111)

            # Create a node.
            download_node = nodes.section()
            download_node.document = self.state.document

            # Parse the rst.
            #nested_parse_with_titles(self.state, rst, node)
            self.state.nested_parse(rst, 0, download_node)

            # Probably could be better here.
            node += download_node.children[0].children[0]

        return [node]

    def is_file(self, rel_file):
        file_path = self.env.relfn2path(rel_file)[1]
        return os.path.isfile(file_path)

    def add_file(self, rel_file):
        file_path = self.env.relfn2path(rel_file)[1]
        md5_hash = md5(file_path)

        # Copy file to _asset build path.
        if os.path.dirname(rel_file):
            target_dir = os.path.join(self.env.app.outdir, '_casts', md5_hash, os.path.dirname(rel_file))
        else:
            target_dir = os.path.join(self.env.app.outdir, '_casts', md5_hash)

        # Prevent uncessary copy
        if self.env.app.builder.name != 'confluence':
            copy_asset(file_path, target_dir)

        # Determine relative path from doc to _asset build path.
        target_file_uri = posixpath.join('_casts', md5_hash, rel_file)
        doc_uri = self.env.app.builder.get_target_uri(self.env.docname)

        return relative_uri(doc_uri, target_file_uri)


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
