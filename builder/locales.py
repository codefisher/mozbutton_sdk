"""Parses the localisation files of the extension and queries it for data"""

import os
import re
import copy
import json
from collections import defaultdict
import codecs
from lxml import etree

ampersand_fix = re.compile(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;|[A-Za-z\.]+;)')

class WebExtensionLocal(object):
    def __init__(self, folder, default_name):
        self._locales = {}
        self._default = default_name
        with open(os.path.join(folder, "messages.json"), "r") as fp:
            self._locales[default_name] = json.load(fp)
        if os.path.exists(os.path.join(folder, "_locales")):
            for locale in os.listdir(os.path.join(folder, "_locales")):
                locale_name = locale.replace("_", "-")
                if locale_name != default_name:
                    with open(os.path.join(folder, "_locales", locale, "messages.json"), "r") as fp:
                        self._locales[locale] = json.load(fp)

    def get_string(self, name, locale):
        if not locale:
            locale = self._default
        locale = locale.replace("-", "_")
        result =  self._locales.get(locale, {}).get(name)
        if result is None:
            result = self._locales.get(self._default, {}).get(name)
        return result

    def get_locales(self):
        return list(self._locales.keys())

def message_name(name):
    def repl(match):
        return match.group(1).upper()
    return re.sub(r'[^a-zA-Z]([a-zA-Z])', repl, name)

class Locale(object):
    """Parses the localisation files of the extension and queries it for data"""
    def __init__(self, settings, folders=None, locales=None):
        self.settings = settings
        self._missing_strings = settings.get("missing_strings")
        self._folders = folders
        self.locales = locales
        self._strings = defaultdict(dict)
        self.files = defaultdict(list)
        self._search_data = {}

        if self._missing_strings == "search":
            with open(os.path.join(
                    settings.get('project_root'),
                    'app_locale', 'strings')) as string_data:
                for line in string_data:
                    string, name, file_name, entities = line.split('\t', 4)
                    for entity in entities.split(','):
                        value = {"name": name, "file_name": file_name}
                        self._search_data[entity.strip()] = value
        include_files = set(self.settings.get("include_locale_files", ()))
        for folder, locale in zip(folders, locales):
            files = [os.path.join(folder, file_name)
                     for file_name in os.listdir(folder)
                     if not file_name.startswith(".")]
            for file_name in files:
                if file_name in include_files:
                    self.files[locale].append(file_name)
                if file_name.endswith(".dtd"):
                    dtd = etree.DTD(file_name)
                    entities = {entity.name: entity.content
                                for entity in dtd.iterentities()}
                    self._strings[locale].update(entities)
                elif file_name.endswith(".properties"):
                    with codecs.open(file_name, encoding='utf-8') as data:
                        lines = (line.strip().split('=', 1)
                                 for line in data if line.strip())
                        properties = {name: value
                                      for (name, value) in lines if name}
                        self._strings[locale].update(properties)

    @classmethod
    def from_locale(cls, settings, locale):
        locale_copy = copy.copy(locale)
        locale_copy.settings = settings
        return locale_copy

    def get_dtd_value(self, locale, name, button=None):
        """Returns the value of a given dtd string

        get_dtd_value(str, str) -> str
        """
        default_locale = self.settings.get("default_locale")
        value = self._strings[locale].get(
            name, self._strings[default_locale].get(name))
        if not value and button and locale == default_locale:
            value = button.get_string(name)
        return value if value else None
    
    def find_string(self, string, locale):
        item = self._search_data.get(string)
        if item is None:
            return None
        name = item.get('name')
        file_name = os.path.join(
            self.settings.get('project_root'),
            item.get('file_name').replace('en-US', locale))
        if not os.path.exists(file_name):
            return None
        elif file_name.endswith(".dtd"):
            return self.find_entities(name, file_name)
        elif file_name.endswith(".properties"):
            return self.find_properties(name, file_name)
        return None

    @staticmethod
    def find_entities(string, path):
        dtd = etree.DTD(path)
        for entity in dtd.iterentities():
            if entity.name in string:
                return entity.content
        return None

    @staticmethod
    def find_properties(string, path):
        with codecs.open(path, encoding='utf-8') as data:
            for line in data:
                if not line.strip() or '=' not in line:
                    continue
                name, value = line.strip().split('=', 1)
                value = value.strip()
                name = name.strip()
                if name in string:
                    return value
        return None
    
    def get_string(self, string, locale=None, button=None):
        default_locale = self.settings.get("default_locale")
        table = self._strings
        if self._missing_strings == "replace":
            def fallback():
                if string in table[default_locale]:
                    return table[default_locale][string]
                else:
                    return button.get_string(string, locale) if button else None
            return table[locale].get(string) or fallback()
        elif self._missing_strings == "empty":
            default = ""
            if button and locale == default_locale:
                default = button.get_string(string, locale)
            return table[locale].get(string, default)
        elif (self._missing_strings == "skip"
              or self._missing_strings == "search"):
            if string in table[locale]:
                return table[locale][string]
            elif (button and locale == default_locale
                  and button.get_string(string, locale)):
                return button.get_string(string, locale)
            elif self._missing_strings == "search":
                value = self.find_string(string, locale)
                if value:
                    return value
        return None

    def _dtd_inter(self, strings, button, line_format, locale, format_type):
        for string in strings:
            value = self.get_string(string, locale, button)
            if value is not None:
                if format_type == "properties":
                    value = (value.replace("&amp;", "&")
                             .replace("&apos;", "'")
                             .replace("&quot;", '"')
                             .replace("&brandShortName;", ''))
                else:
                    value = (ampersand_fix.sub('&amp;', value)
                             .replace("'", "&apos;")
                             .replace('"', "&quot;"))
                yield line_format.format(string, value)

    def get_dtd_data(self, strings, button=None,
                     untranslated=True, format_type="dtd"):
        """Gets a set of files with all the strings wanted

        get_dtd_data(list<str>) -> dict<str: str>
        """
        strings = list(strings)
        if self.settings.get("include_toolbars"):
            strings.extend((
                "tb-toolbar-buttons-toggle-toolbar.label",
                "tb-toolbar-buttons-toggle-toolbar.tooltip",
                "tb-toolbar-buttons-toggle-toolbar.name"))

        if self.settings.get("menuitems") and self.settings.get("menu_meta"):
            _, menu_label, _ = self.settings.get("menu_meta")
            strings.append(menu_label)
        return self.get_string_data(strings, button, untranslated, format_type)

    def get_properties_data(self, strings, button=None):
        """Gets a set of files with all the .properties strings wanted

        get_properties_data(list<str>) -> dict<str: str>
        """
        default_locale = self.settings.get("default_locale")
        result = {}
        for locale in self.locales:
            properties_file = []
            for string in strings:
                value = self.get_string(string, locale, button)
                if value is not None:
                    properties_file.append(u"{}={}".format(string, value))
            if self.settings.get("translate_description"):
                pref = "extensions.{}.description".format(
                    self.settings.get("extension_id"))
                if locale == default_locale:
                    description = re.sub(
                        r'[\r\n]+', r'\\n ', self.settings.get("description"))
                    properties_file.append(u"{}={}".format(pref, description))
                elif pref in self._strings[locale]:
                    description = self._strings[locale][pref]
                    properties_file.append(u"{}={}".format(pref, description))
            result[locale] = "\n".join(properties_file)
        return result

    def get_string_data(self, strings, button=None,
                        untranslated=True, format_type="dtd"):
        default = self.settings.get("default_locale")
        if format_type == "properties":
            line_format = u"{}={}"
        else:
            line_format = u"""<!ENTITY {} "{}">"""
        result = {}
        strings = list(strings)
        for locale in self.locales:
            for string in strings:
                if self._strings[locale].get(string):
                    break
            else:
                if not untranslated and locale != default:
                    continue
            result[locale] = "\n".join(self._dtd_inter(
                strings, button, line_format, locale, format_type))
        return result

    def get_string_dict(self, strings, button=None,
                        untranslated=True):
        default = self.settings.get("default_locale")
        result = {}
        strings = list(strings)
        for locale in self.locales:
            for string in strings:
                if self._strings[locale].get(string):
                    break
            else:
                if not untranslated and locale != default:
                    continue
            result[locale] = {}
            for string in strings:
                value = self.get_string(string, locale, button)
                if value is not None:
                    result[locale][string] = value
        return result
