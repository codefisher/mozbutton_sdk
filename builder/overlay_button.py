import os
import re
import json
import io # we might not need this as much now, that PIL as .tobytes()
import math
import hashlib
from collections import defaultdict
import grayscale
from util import get_pref_folders
import lxml.etree as ET
try:
    from PIL import Image
except ImportError:
    pass

from ext_button import Button

class OverlayButton(Button):
    
    def get_xul_files(self):
        """

        Precondition: get_js_files() has been called
        """
        button_hash, toolbar_template = self._get_toolbar_info()
        with open(os.path.join(self._settings.get("button_sdk_root"), 'templates', 'button.xul')) as template_file:
            template = template_file.read()
        result = {}
        for file_name, values in self._button_xul.iteritems():
            js_includes = []
            for js_file in self._get_js_file_list(file_name):
                js_includes.append("""<script type="application/x-javascript" src="chrome://%s/content/%s.js"/>""" % (self._settings.get("chrome_name"), js_file))
            toolbars, toolbar_ids = self._wrap_create_toolbar(button_hash, toolbar_template, file_name, values)
            menu = self._create_menu(file_name, values) if self._settings.get("menuitems") else ""
            xul_file = (template.replace("{{buttons}}", "\n  ".join(values.values()))
                                .replace("{{script}}", "\n ".join(js_includes))
                                .replace("{{keyboard_shortcut}}", self.get_keyboard_shortcuts(file_name))
                                .replace("{{chrome-name}}", self._settings.get("chrome_name"))
                                .replace("{{locale_file_prefix}}", self._settings.get("locale_file_prefix"))
                                .replace("{{toolbars}}", toolbars)
                                .replace("{{palette}}", self._settings.get("file_to_palette").get(file_name, ""))
                                .replace("{{menu}}", menu)
                        )
            result[file_name] = xul_file
        return result