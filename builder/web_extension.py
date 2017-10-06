import os
import json
import re
from builder.ext_button import Button, get_image, ExtensionConfigError, bytes_string
from builder.locales import WebExtensionLocal, message_name



class WebExtensionButton(Button):

    def __init__(self, folders, buttons, settings, applications):
        super(WebExtensionButton, self).__init__(folders, buttons, settings, applications)
        self._button_background_js = {}
        self.popup_files = {}
        self.option_files = {}
        self.webx_locale = None


        if len(buttons) != 1 or len(self._manifests) != 1 or len(self._info) != 1:
            raise ExtensionConfigError("WebExtensions can only have a single button in them. " + ", ".join(buttons))
        self.the_button = buttons[0]

        if len(self._manifests) == 0:
            raise ExtensionConfigError(
                "Buttons for WebExtensions must have a manifest.json file.")


        button, data = list(self._manifests.items())[0]
        if "images" in data:
            self._icons[button] = data.get('images')
        if "strings" in data: # looking to remove
            for name, value in data.get("strings"):
                self._strings[name] = value
        self._name_of_ext = data.get("name")

        folder, button, files = self._info[0]
        if "messages.json" in files:
            self.webx_locale = WebExtensionLocal(folder, settings.get('default_locale'))
        if 'background.js' in files:
            with open(os.path.join(folder, "background.js"), "r") as background:
                self._button_background_js[button] = background.read()
        for file_group, file_var in (
                ('popup', self.popup_files),
                ('option', self.option_files)):
            if file_group in files:
                for file_name in os.listdir(os.path.join(folder, file_group)):
                    if file_name[0] != ".":
                        path = os.path.join(folder, file_group, file_name)
                        file_var[file_name] = path


    def get_file_strings(self, settings, button_locales):
        manifest = {
            "manifest_version": 2,
            "name": "__MSG_extensionName__",
            "version": settings.get('version'),
            "description": "__MSG_extensionDescription__",
            "homepage_url": settings.get('homepage'),
            "author": settings.get('creator'),
            "icons": {},
            "browser_action": {
                "browser_style": True,
                "default_icon": {},
            },
            "applications": {
                "gecko": {
                    "id": settings.get('extension_id'),
                    "strict_min_version": "42.0"
                }
            },
            "default_locale": settings.get('default_locale').replace('-', '_'),
        }
        if settings.get('homepage'):
            manifest["homepage_url"] = settings.get('homepage')
        data = self._manifests.get(self.the_button)
        if 'default_title' in data:
            manifest['browser_action']["default_title"] = "__MSG_{}__".format(message_name(data.get('default_title')))
        if 'content_scripts' in data:
            manifest['content_scripts'] = data.get('content_scripts')
        if 'web_accessible_resources' in data:
            manifest['web_accessible_resources'] = data.get('web_accessible_resources')
        if 'permissions' in data:
            manifest['permissions'] = data['permissions']
        for size in settings.get('icon_size'):
            name = "icons/{}-{}".format(size, settings.get("icon"))
            manifest['icons'][size] = name
            manifest['browser_action']['default_icon'][size] = name
        if self.popup_files:
            manifest['browser_action']['default_popup'] = 'popup/panel.html'
        if self.option_files:
            manifest["options_ui"] = {"page": 'option/option.html', "browser_style": True}
        background_scripts = []
        for button, data in self._button_background_js.items():
            name = 'background.js'
            yield name, data
            background_scripts.append(name)
        for locale, name, data in self.locale_files(button_locales):
            yield "_locales/{}/{}".format(locale.replace('-', '_'), name), data
        def option_fix(match):
            return "__MSG_{}__".format(message_name(match.group(1)))

        for file_group, file_var in (
                ('popup', self.popup_files),
                ('option', self.option_files),
                ('files', self.extra_files)):
            for name, path in file_var.items():
                if name.endswith(".html"):
                    with open(path, 'r') as fp:
                        yield (os.path.join(file_group, name), re.sub('__MSG_(.*?)__', option_fix, fp.read()))
        if 'background' in data:
            manifest['background'] = data['background']
        elif background_scripts:
            manifest['background'] = {'scripts': background_scripts}
        yield 'manifest.json', json.dumps(manifest, indent=4, sort_keys=True)

    def get_files_names(self, settings):
        for size in settings.get('icon_size'):
            path = get_image(settings, size, settings.get("icon"))
            yield (path, "icons/{}-{}".format(size, settings.get("icon")))
        for name, path in self.extra_files.items():
            manifiest = self._manifests.get(self.the_button)
            if (not name.endswith('.xul') and not name.endswith('.html')
                and (manifiest.get('files') is None
                     or name in manifiest.get('files'))):
                yield (path, os.path.join('files', name))
        for name, path in self.popup_files.items():
            if not name.endswith(".html"):
                yield (path, os.path.join('popup', name))
        for name, path in self.option_files.items():
            if not name.endswith(".html"):
                yield (path, os.path.join('option', name))
        if self.option_files or self.popup_files or self.extra_files:
            yield os.path.join(settings.get('button_sdk_root'), 'templates', 'localise.js'), "localise.js"


    def get_string(self, name, locale=None):
        # we always return them here, because we are still in transition and they don't exist.
        if name == "extensionName":
            return self._name_of_ext
        elif name == "extensionDescription":
            return self._settings.get('description').strip()
        if self.webx_locale:
            result = self.get_web_ext_string(name, locale)
            if result:
                return result.get("message")
        return super(WebExtensionButton, self).get_string(name, locale)


    def meta_strings(self, name, locale):
        if locale == self._settings.get("default_locale"):
            if name == "extensionName":
                return {
                    "message": self._name_of_ext,
                    "description": "Name of the extension."
                }
            elif name == "extensionDescription":
                return {
                    "message": self._settings.get('description').strip(),
                    "description": "Description of the extension."
                }
        return

    def get_web_ext_string(self, name, locale):
        result = self.meta_strings(name, locale)
        if result:
            return result
        result = self.webx_locale.get_string(name, locale)
        if result:
            return result
        else:
            result = self.webx_locale.get_string(message_name(name), locale)
            if result:
                return result
        return None

    def get_string_info(self, name, locale=None):
        result = self.meta_strings(name, locale)
        if result:
            return result
        if self.webx_locale:
            result = self.get_web_ext_string(name, locale)
            if result:
                if not result.get("description"):
                    default_result = self.get_web_ext_string(name, self._settings.get("default_locale"))
                    result["description"] = default_result.get("description", "")
                return result
        string = self.get_string(name, locale)
        return {
            "description": "",
            "message": string
        }

    def locale_files(self, button_locales, *args, **kwargs):
        if self.webx_locale:
            for locale in self.webx_locale.get_locales():
                strings = {}
                for string in self.get_locale_strings():
                    strings[message_name(string)] = self.get_string_info(string, locale)
                yield locale, "messages.json", json.dumps(strings, sort_keys=True, indent=2)
        else:
            # this really amounts to importing from the old format
            data = button_locales.get_string_dict(self.get_locale_strings(), self, untranslated=False)
            for locale, values in data.items():
                strings = {}
                for string, value in values.items():
                    if isinstance(value, dict):
                        strings[message_name(string)] = value
                    else:
                        strings[message_name(string)] = {"message": value, "description": ""}
                yield locale, "messages.json", json.dumps(strings, sort_keys=True, indent=2)

    def get_locale_strings(self):
        strings = {"extensionName", "extensionDescription"}
        data = self._manifests.get(self.the_button)
        if 'default_title' in data:
            strings.add(data.get('default_title'))
        if 'used_strings' in data:
            strings.update(data.get('used_strings'))
        if 'strings' in data:
            for name, _ in data.get("strings"):
                strings.add(name)
        if 'messages' in data:
            strings.update(data["messages"].keys())
        for file_group in (self.popup_files, self.option_files, self.extra_files):
            for name, path in file_group.items():
                if name.endswith('.html'):
                    with open(path, 'r') as fp:
                        for match in re.finditer('__MSG_(.*?)__', fp.read()):
                            strings.add(match.group(1))
        return strings