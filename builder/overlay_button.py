import os
import lxml.etree as ET
try:
    from PIL import Image
except ImportError:
    pass
import operator
import itertools
import json

from builder.ext_button import Button, ChromeString

class OverlayButton(Button):

    def get_js_files(self):
        js_files = super(OverlayButton, self).get_js_files()
        show_updated_prompt = self._settings.get("show_updated_prompt")
        add_to_main_toolbar = self._settings.get("add_to_main_toolbar")
        if show_updated_prompt or add_to_main_toolbar:
            update_file = self.env.get_template("update.js")
            show_update = update_file.render(
                show_updated_prompt=show_updated_prompt,
                add_to_main_toolbar=bool(add_to_main_toolbar),
                buttons=json.dumps(add_to_main_toolbar),
                current_version_pref=self._settings.get("current_version_pref"),
                uuid=self._settings.get("extension_id"),
                version=self._settings.get("version"),
                homepage_url=self._settings.get("homepage"),
                javascript_object=self._settings.get("javascript_object")
            )
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
            fiile_name = os.path.join("defaults", "preferences", "defaultprefs.js")
            yield ChromeString(file_name=fiile_name, data=defaults)

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
        for file_name in self._button_files:
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
        javascript_object = self._settings.get("javascript_object")
        if not self._settings.get('menuitems'):
            return ''
        menu_id, menu_label, location = self._settings.get("menu_meta")
        statements = []
        data = self.create_menu_dom(file_name, buttons)
        in_submenu = [menuitem for menuitem in data if menuitem.parent_id is None]
        in_menu = [(menuitem.parent_id, menuitem) for menuitem in data
                        if menuitem.parent_id is not None]
        meta = self._settings.get("file_to_menu").get(location, {}).get(file_name)
        if in_submenu and meta:
            menupopup = ET.Element("menupopup")
            for item, _, _ in in_submenu:
                menupopup.append(item)
            menu_name, insert_after = meta
            menu = ET.Element("menu", {"insertafter": insert_after, "id": menu_id, "label": "&%s;" % menu_label })
            if self._settings.get('menuitems_sorted'):
                onpopupshowing = "{0}.sortMenu(event, this); {0}.handelMenuLoaders(event, this);".format(javascript_object)
            else:
                onpopupshowing = "{0}.handelMenuLoaders(event, this);".format(javascript_object)
            menupopup.attrib.update({
                "sortable": "true",
                "onpopupshowing": onpopupshowing,
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

    def get_keyboard_shortcuts(self, file_name):
        if not self._settings.get("use_keyboard_shortcuts") or not self._settings.get("file_to_keyset").get(file_name):
            return ""
        keys = []
        pref_root = self._settings.get('pref_root')
        for button, (key, modifier) in self._button_keys.items():
            attr = 'key' if len(key) == 1 else "keycode"
            if file_name in self._button_xul:
                mod = "" if not modifier else 'modifiers="&%smodifier.%s;" ' % (pref_root, button)
                command = self._button_commands.get(file_name, {}).get(button)
                if command:
                    keys.append("""<key %s="&%skey.%s;" %sid="%s-key" oncommand="%s" />""" % (attr, pref_root, button, mod, button, command))
                else:
                    if self._settings.get("menuitems"):
                        keys.append("""<key %s="&%skey.%s;" %sid="%s-key" command="%s-menu-item" />""" % (attr, pref_root, button, mod, button, button))
                    else:
                        keys.append("""<key %s="&%skey.%s;" %sid="%s-key" command="%s" />""" % (attr, pref_root, button, mod, button, button))
        if keys:
            return """\n <keyset id="%s">\n\t%s\n </keyset>""" % (self._settings.get("file_to_keyset").get(file_name), "\n\t".join(keys))
        else:
            return ""

    def _create_toolbar(self, button_hash, toolbar_template, file_name, values):
        toolbar_ids = []
        tool_bars = []
        bottom_bars = []
        if file_name in self._settings.get("extra_toolbars_disabled"):
            return tool_bars, bottom_bars, toolbar_ids
        count = 0
        max_count = self._settings.get("buttons_per_toolbar")
        buttons = values.keys()
        for box_setting, include_setting, toolbars in [("file_to_toolbar_box", "include_toolbars", tool_bars),
                                                       ("file_to_bottom_box", "include_satusbars", bottom_bars)]:
            toolbar_node, toolbar_box = self._settings.get(box_setting).get(file_name, ('', ''))
            if self._settings.get(include_setting) and toolbar_box:
                number = self.toolbar_count(include_setting, values, max_count)
                defaultset = ""
                for i in range(number):
                    if self._settings.get("put_button_on_toolbar"):
                        defaultset = 'defaultset="%s"' % ",".join(buttons[i * max_count:(i + 1) * max_count])
                    button_hash.update(str(i))
                    hash_code = button_hash.hexdigest()[:6]
                    label_number = "" if (number + count) == 1 else " %s" % (i + count + 1)
                    toolbar_ids.append("tb-toolbar-%s" % hash_code)
                    toolbar_box_id = "" if include_setting == "include_toolbars" else 'toolboxid="%s" ' % toolbar_box
                    toolbars.append('''<toolbar %spersist="collapsed,hidden" context="toolbar-context-menu" class="toolbar-buttons-toolbar chromeclass-toolbar" id="tb-toolbar-%s" mode="icons" iconsize="small" customizable="true" %s toolbarname="&tb-toolbar-buttons-toggle-toolbar.name;%s"/>''' % (toolbar_box_id, hash_code, defaultset, label_number))
                    values["tb-toolbar-buttons-toggle-toolbar-%s" % hash_code] = toolbar_template.replace("{{hash}}", hash_code).replace("{{ number }}", label_number)
                count += number
        return tool_bars, bottom_bars, toolbar_ids

    def _wrap_create_toolbar(self, button_hash, toolbar_template, file_name, values):
        tool_bars, bottom_box, toolbar_ids = self._create_toolbar(button_hash, toolbar_template, file_name, values)
        if not tool_bars and not bottom_box:
            return '', []
        result = []
        for toolbars, box_setting in ((tool_bars, "file_to_toolbar_box"), (bottom_box, "file_to_bottom_box")):
            if not toolbars:
                continue
            toolbar_node, toolbar_box = self._settings.get(box_setting).get(file_name, ('', ''))
            result.append('\n<%s id="%s">\n%s\n</%s>' % (toolbar_node, toolbar_box, '\n'.join(toolbars), toolbar_node))
        return "\n\t".join(result), toolbar_ids