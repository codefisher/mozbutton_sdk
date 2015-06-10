"""Parses the localisation files of the extension and queries it for data"""

import os
import re
from collections import defaultdict
import codecs
from lxml import etree

entity_re = re.compile(r"<!ENTITY\s+([\w\-\.]+?)\s+[\"'](.*?)[\"']\s*>")
ampersand_fix = re.compile(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)')

class Locale(object):
    """Parses the localisation files of the extension and queries it for data"""
    def __init__(self, settings, folders=None, locales=None, options=False, 
                 load_properites=True, only_meta=False, all_files=False,
                 local_obj=None):
        self._settings = settings
        if local_obj:
            self._missing_strings = local_obj._missing_strings
            self._folders = local_obj._folders
            self._locales = local_obj._locales
            self._strings = local_obj._strings
            self._meta = local_obj._meta
            self._search_data = local_obj._search_data
            return
        elif folders and locales:
            self._missing_strings = settings.get("missing_strings")
            self._folders = folders
            self._locales = locales
            self._strings = defaultdict(dict)
            self._meta = {}
            self._search_data = {}
        else:
            raise ValueError("Not able to make Locale")
        
        if self._missing_strings == "search":
            with open(os.path.join(settings.get('project_root'), 'app_locale', 'strings')) as string_data:
                for line in string_data:
                    string, name, file_name, entities = line.split('\t', 4)
                    for entity in entities.split(','):
                        self._search_data[entity.strip()] = {"name": name, "file_name": file_name}
        
        for folder, locale in zip(folders, locales):
            files = [os.path.join(folder, file_name)
                     for file_name in os.listdir(folder)
                     if not file_name.startswith(".")]
            for file_name in files:
                if not all_files:
                    if only_meta and not file_name.endswith("meta.dtd"):
                        continue
                    if not options and file_name.endswith("options.dtd"):
                        continue
                    elif options and not file_name.endswith("options.dtd"):
                        continue
                    elif not load_properites and file_name.endswith(".properties"):
                        continue
                if file_name.endswith(".dtd"):
                    if file_name.endswith("meta.dtd"):
                        self._meta[locale] = file_name
                    dtd = etree.DTD(file_name)
                    self._strings[locale].update({entity.name: entity.content for entity in dtd.iterentities()})
                elif file_name.endswith(".properties"):
                    with codecs.open(file_name, encoding='utf-8') as data:
                         self._strings[locale].update({name: value for (name, value) in
                                    (line.strip().split('=', 1) for line in data if line.strip()) if name})
    def get_meta(self):
        return self._meta.items()

    def get_locales(self):
        return self._locales

    def get_dtd_value(self, locale, name, button=None):
        """Returns the value of a given dtd string

        get_dtd_value(str, str) -> str
        """
        value = self._strings[locale].get(name,
                self._strings[self._settings.get("default_locale")].get(name))
        if not value and button and locale == self._settings.get("default_locale"):
            value = button.get_string(name)
        return value if value else None
    
    def find_string(self, string, locale):
        item = self._search_data.get(string)
        if item == None:
            return None
        name = item.get('name')
        file_name = os.path.join(self._settings.get('project_root'), item.get('file_name').replace('en-US', locale))
        if not os.path.exists(file_name):
            return None
        elif file_name.endswith(".dtd"):
            return self.find_entities(name, file_name)
        elif file_name.endswith(".properties"):
            return self.find_properties(name, file_name)
        return None
    
    def find_entities(self, string, path):
        # TODO: user dtd parser
        with codecs.open(path, encoding='utf-8') as data:
            for line in data:
                match = entity_re.match(line.strip())
                if match:
                    name, value = match.group(1), match.group(2)
                    if name in string:
                        return value
        return None
                        
    def find_properties(self, string, path):
        with codecs.open(path, encoding='utf-8') as data:
            for line in data:
                if not line.strip() or not '=' in line:
                    continue
                name, value = line.strip().split('=', 1)
                value = value.strip()
                name = name.strip()
                if name in string:
                    return value
        return None
    
    def get_string(self, string, locale=None, button=None):
        default_locale = self._settings.get("default_locale")
        table = self._strings
        if self._missing_strings == "replace":
            def fallback():
                if string in table[default_locale]:
                    return table[default_locale][string]
                else:
                    return button.get_string(string, locale) if button else None
            return table[locale].get(string) or fallback()
        elif self._missing_strings == "empty":
            return table[locale].get(string, 
                            button.get_string(string, locale) if button and locale == default_locale else "")
        elif self._missing_strings == "skip" or self._missing_strings == "search":
            if string in table[locale]:
                return table[locale][string]
            elif button and locale == default_locale and button.get_string(string, locale):
                return button.get_string(string, locale)
            elif self._missing_strings == "search":
                value = self.find_string(string, locale)
                if value:
                    return value
        return None


    def _dtd_inter(self, strings, button, format, locale, format_type):
        for string in strings:
            value = self.get_string(string, locale, button)
            if value is not None:
                if format_type == "properties":
                    value = value.replace("&amp;", "&").replace("&apos;", "'").replace("&quot;", '"').replace("&brandShortName;", '')
                else:
                    value = ampersand_fix.sub('&amp;', value).replace("'", "&apos;").replace('"', "&quot;")
                yield format % (string, value)

    def get_dtd_data(self, strings, button=None, untranslated=True, format_type="dtd"):
        """Gets a set of files with all the strings wanted

        get_dtd_data(list<str>) -> dict<str: str>
        """
        default = self._settings.get("default_locale")
        if format_type == "properties":
            format = "%s=%s"
        else:
            format = """<!ENTITY %s "%s">"""
        result = {}
        strings = list(strings)
        if self._settings.get("include_toolbars"):
            strings.extend((
                   "tb-toolbar-buttons-toggle-toolbar.label",
                   "tb-toolbar-buttons-toggle-toolbar.tooltip",
                   "tb-toolbar-buttons-toggle-toolbar.name"))
        if self._settings.get("menuitems") and self._settings.get("menu_meta"):
            _, menu_label, _ = self._settings.get("menu_meta")
            strings.append(menu_label)
        for locale in self._locales:
            for string in strings:
                if self._strings[locale].get(string):
                    break
            else:
                if not untranslated and locale != default:
                    continue
            result[locale] = "\n".join(self._dtd_inter(strings, button, format, locale, format_type))
        return result

    def get_properties_data(self, strings, button=None):
        """Gets a set of files with all the .properties strings wanted

        get_properties_data(list<str>) -> dict<str: str>
        """
        default_locale = self._settings.get("default_locale")
        result = {}
        for locale in self._locales:
            properties_file = []
            for string in strings:
                value = self.get_string(string, locale, button)
                if value is not None:
                    properties_file.append("%s=%s" % (string, value))
            if self._settings.get("translate_description"):
                description = "extensions.%s.description" % self._settings.get("extension_id")
                if locale == default_locale:
                    properties_file.append("%s=%s" % (description, re.sub(r'[\r\n]+', r'\\n ', self._settings.get("description"))))
                elif description in self._strings[locale]:
                    properties_file.append("%s=%s" % (description, self._strings[locale][description]))
            result[locale] = "\n".join(properties_file)
        return result

    def get_string_data(self, strings, button=None, untranslated=True, format_type="dtd"):
        default = self._settings.get("default_locale")
        if format_type == "properties":
            format = "%s=%s"
        else:
            format = """<!ENTITY %s "%s">"""
        result = {}
        strings = list(strings)
        for locale in self._locales:
            result[locale] = "\n".join(self._dtd_inter(strings, button, format, locale, format_type))
        return result