import os
import lxml.etree as ET
try:
    from PIL import Image
except ImportError:
    pass
import operator
import itertools

from builder.ext_button import Button, ChromeString

class OverlayButton(Button):

    def get_js_files(self):
        js_files = super(OverlayButton, self).get_js_files()
        if self._settings.get("show_updated_prompt") or self._settings.get("add_to_main_toolbar"):
            update_file = os.path.join(self._settings.get("project_root"), "files", "update.js")
            if not os.path.isfile(update_file):
                update_file = os.path.join(self._settings.get('button_sdk_root'), "templates", "update.js")
            with open(update_file, "r") as update_js:
                show_update = (update_js.read()
                           .replace("{{uuid}}", self._settings.get("extension_id"))
                           .replace("{{homepage_url}}",
                                    self._settings.get("homepage"))
                           .replace("{{version}}",
                                    self._settings.get("version"))
                           .replace("{{chrome_name}}",
                                    self._settings.get("chrome_name"))
                           .replace("{{current_version_pref}}",
                                    self._settings.get("current_version_pref"))
                           )
            if self._settings.get("show_updated_prompt"):
                show_update += "load_toolbar_button.callbacks.push(load_toolbar_button.load_url);\n"
            if self._settings.get("add_to_main_toolbar"):
                buttons = ", ".join("'%s'" % item for item in self._settings.get("add_to_main_toolbar"))
                show_update += "load_toolbar_button.callbacks.push(function(previousVersion, currentVersion) { if(previousVersion == '') { load_toolbar_button.add_buttons([%s]);} });\n" % buttons
            js_files["button"] = show_update + "\n" + js_files["button"]
        return js_files

    def get_files(self):
        for file_name, data in self.get_xul_files().items():
            yield (file_name + ".xul", data)

    def get_chrome_strings(self):
        for chrome_string in super(OverlayButton, self).get_chrome_strings():
            yield chrome_string
        defaults =  self.get_defaults()
        if defaults:
            yield ChromeString(file_name=os.path.join("defaults", "preferences", "toolbar_buttons.js"), data=defaults)

    def locale_files(self, button_locales, *args, **kwargs):
        dtd_data = button_locales.get_dtd_data(self.get_locale_strings(),
            self, untranslated=False)
        for locale, data in dtd_data.items():
            yield locale, "button.dtd", data
        locales_inuse = dtd_data.keys()
        for locale, file_name, data in super(OverlayButton, self).locale_files(
                button_locales, locales_inuse):
            yield locale, file_name, data

    def manifest_lines(self):
        lines = super(OverlayButton, self).manifest_lines()
        chrome_name=self._settings.get("chrome_name")
        lines.append("style\tchrome://global/content/customizeToolbar.xul"
                     "\tchrome://{chrome}/skin/button.css".format(chrome=chrome_name))
        if self.resource_files:
            lines.append("resource\t{chrome}\tchrome://{chrome}/content/resources/".format(chrome=chrome_name))
        for file_name in self.get_file_names():
            for overlay in self._settings.get("files_to_overlay").get(file_name, ()):
                lines.append("overlay\t{overlay}\t"
                             "chrome://{chrome}/content/{file_name}.xul".format(chrome=chrome_name, file_name=file_name, overlay=overlay))
        return lines

    def get_locale_strings(self):
        strings = super(OverlayButton, self).get_locale_strings()
        pref_root = self._settings.get('pref_root')
        for button in self._button_keys.keys():
            strings.extend(["%s.key.%s" % (pref_root, button), "%s.modifier.%s" % (pref_root, button)])
        return strings

    def _create_menu(self, file_name, buttons):
        if not self._settings.get('menuitems'):
            return ''
        menu_id, menu_label, location = self._settings.get("menu_meta")
        statements = []
        data = self.create_menu_dom(file_name, buttons)
        in_submenu = {button: menuitem for button, menuitem in data.items() if menuitem.parent_id is None}
        in_menu = [(menuitem.parent_id, menuitem) for button, menuitem in data.items()
                        if menuitem.parent_id is not None]
        meta = self._settings.get("file_to_menu").get(location, {}).get(file_name)
        if in_submenu and meta:
            menupopup = ET.Element("menupopup")
            for item, _, _ in in_submenu.values():
                menupopup.append(item)
            menu_name, insert_after = meta
            menu = ET.Element("menu", {"insertafter": insert_after, "id": menu_id, "label": "&%s;" % menu_label })
            menupopup.attrib.update({
                "sortable": "true",
                "onpopupshowing": "toolbar_buttons.sortMenu(event, this); toolbar_buttons.handelMenuLoaders(event, this);",
                "id": "%s-popup" % menu_id,
            })
            menu.append(menupopup)
            overlay_menupopup = ET.Element("menupopup", {"id": menu_name})
            overlay_menupopup.append(menu)
            statements.append(ET.tostring(overlay_menupopup, pretty_print=True).replace("&amp;", "&"))
        if in_menu:
            for menu_name, items in itertools.groupby(sorted(in_menu), key=operator.itemgetter(0)):
                menupopup = ET.Element("menupopup", {"id": menu_name})
                for _, (item, menu_name, insert_after) in items:
                    item.attrib['insertafter'] = insert_after
                    menupopup.append(item)
                statements.append(ET.tostring(menupopup, pretty_print=True).replace("&amp;", "&"))
        return '\n\t'.join(statements)

    def get_xul_files(self):
        """

        Precondition: get_js_files() has been called
        """
        button_hash, toolbar_template = self._get_toolbar_info()
        with open(os.path.join(self._settings.get("button_sdk_root"), 'templates', 'button.xul')) as template_file:
            template = template_file.read()
        result = {}
        for file_name, values in self._button_xul.items():
            js_includes = []
            for js_file in self._get_js_file_list(file_name):
                js_includes.append("""<script type="application/x-javascript" src="chrome://%s/content/%s.js"/>""" % (self._settings.get("chrome_name"), js_file))
            toolbars, toolbar_ids = self._wrap_create_toolbar(button_hash, toolbar_template, file_name, values)
            menu = self._create_menu(file_name, values) if self._settings.get("menuitems") else ""
            xul_file = (template.replace("{{buttons}}", "\n  ".join(values.values()))
                                .replace("{{script}}", "\n ".join(js_includes))
                                .replace("{{keyboard_shortcut}}", self.get_keyboard_shortcuts(file_name))
                                .replace("{{chrome_name}}", self._settings.get("chrome_name"))
                                .replace("{{locale_file_prefix}}", self._settings.get("locale_file_prefix"))
                                .replace("{{toolbars}}", toolbars)
                                .replace("{{palette}}", self._settings.get("file_to_palette").get(file_name, ""))
                                .replace("{{menu}}", menu)
                        )
            result[file_name] = xul_file
        return result