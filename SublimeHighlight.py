# -*- coding: utf-8 -*-

"""
    TODO:
    - customize rendered HTML to ease choosing a new theme
"""

import desktop
import os
import pygments
import re
import sublime
import sublime_plugin
import subprocess
import tempfile

from pygments import highlight
from pygments.lexers import *
from pygments.formatters import *
from pygments.styles import STYLE_MAP

# Don't judge me. Just don't. If you knew, you wouldn't.
for s in STYLE_MAP:
    __import__('pygments.styles.%s' % s)


DEFAULT_STYLE = "default"
FORMATS = ('html', 'rtf',)

settings = sublime.load_settings('%s.sublime-settings' % __name__)


class SublimeHighlightCommand(sublime_plugin.TextCommand):
    """Code highlighter command."""

    @property
    def code(self):
        return self.view.substr(self.region)

    @property
    def encoding(self):
        encoding = self.view.encoding()
        if encoding == 'Undefined':
            encoding = 'utf-8'
        elif encoding == 'Western (Windows 1252)':
            encoding = 'windows-1252'
        return encoding

    @property
    def region(self):
        regions = self.view.sel()
        if len(regions) > 0 and regions[0].size() > 0:
            return regions[0]
        else:
            return sublime.Region(0, self.view.size())

    def guess_lexer_from_syntax(self):
        syntax = self.view.settings().get('syntax')
        if not syntax:
            return
        match = re.match(r"Packages/.*/(.*?)\.tmLanguage$", syntax)
        if not match:
            return
        try:
            return pygments.lexers.get_lexer_by_name(match.group(1).lower())
        except pygments.util.ClassNotFound:
            return

    def get_formatter(self, output_type, full=True):
        return pygments.formatters.get_formatter_by_name(output_type,
            linenos=settings.get('linenos', False),
            noclasses=settings.get('noclasses', False),
            style=settings.get('theme', DEFAULT_STYLE),
            full=settings.get('full', True),
            fontface=settings.get('fontface', ''))

    def get_lexer(self, code=None):
        code = code if code is not None else self.code
        lexer = None
        if self.view.file_name():
            try:
                lexer = pygments.lexers.get_lexer_for_filename(
                    self.view.file_name(), code)
            except pygments.util.ClassNotFound:
                pass
        if not lexer:
            lexer = self.guess_lexer_from_syntax()
        if not lexer:
            lexer = pygments.lexers.guess_lexer(code)
        return lexer

    def highlight(self, output_type):
        return highlight(self.code, self.get_lexer(),
            self.get_formatter(output_type))

    def run(self, edit, target='external', output_type='html'):
        output_type = output_type if output_type in FORMATS else 'html'
        pygmented = self.highlight(output_type)

        if target == 'external':
            filename = '%s.%s' % (self.view.id(), output_type,)
            tmp_file = self.write_file(filename, pygmented)
            sublime.status_message(u'Written %s preview file: %s'
                                   % (output_type.upper(), tmp_file))
            if desktop.get_desktop() == 'Mac OS X':
                # for some reason desktop.open is broken under OSX Lion
                subprocess.call("open %s" % tmp_file, shell=True)
            else:
                desktop.open(tmp_file)
        elif target == 'clipboard':
            if desktop.get_desktop() == 'Mac OS X':
                # on mac osx we have `pbcopy` :)
                filename = '%s.%s' % (self.view.id(), output_type,)
                tmp_file = self.write_file(filename, pygmented)
                subprocess.call("cat %s | pbcopy -Prefer %s"
                                % (tmp_file, output_type,), shell=True)
                os.remove(tmp_file)
            else:
                sublime.set_clipboard(pygmented)
        elif target == 'sublime':
            new_view = self.view.window().new_file()
            if output_type == 'html':
                new_view.set_syntax_file('Packages/HTML/HTML.tmLanguage')
            new_edit = new_view.begin_edit()
            new_view.insert(new_edit, 0, pygmented)
            new_view.end_edit(new_edit)
        else:
            sublime.error_message(u'Unsupported target "%s"' % target)

    def write_file(self, filename, contents, encoding=None):
        """Writes highlighted contents onto the filesystem."""
        encoding = encoding if encoding is not None else self.encoding
        tmp_fullpath = os.path.join(tempfile.gettempdir(), filename)
        tmp_file = open(tmp_fullpath, 'w')
        tmp_file.write(contents.encode(encoding))
        tmp_file.close()
        return tmp_fullpath
