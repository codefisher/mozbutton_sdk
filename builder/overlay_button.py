import os
import lxml.etree as ET
try:
    from PIL import Image
except ImportError:
    pass
import operator
import itertools

from ext_button import Button

class OverlayButton(Button):

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
            statements.append(ET.tostring(menupopup, pretty_print=True).replace("&amp;", "&"))
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