import os
import re
import json
import codecs
import lxml.etree as ET
from copy import deepcopy
try:
    from PIL import Image
except ImportError:
    pass

from builder.ext_button import Button

class RestartlessButton(Button):

    def __init__(self, *args, **kwargs):
        super(RestartlessButton, self).__init__(*args, **kwargs)
        self._ui_ids = set()
    
    def jsm_keyboard_shortcuts(self, file_name):
        if not self._settings.get("use_keyboard_shortcuts"):
            return ""
        statements = []
        for i, button in enumerate(self._button_keys.keys()):
            func = self._button_commands.get(file_name, {}).get(button)
            if func is None:
                continue
            command = self._patch_call(func)
            statements.append("""var key_%(num)s = document.createElement('key');
	key_%(num)s.id = '%(button)s-key';
	key_%(num)s.setAttribute('oncommand', 'void(0);');
	key_%(num)s.addEventListener('command', function(event) {
				%(command)s
			}, false);
	var key_disabled_%(num)s = extensionPrefs.getBoolPref("key-disabled.%(button)s");
	key_%(num)s.setAttribute('disabled', key_disabled_%(num)s);
	if(!key_disabled_%(num)s) {
		setKeyCode(key_%(num)s, extensionPrefs.getComplexValue("key.%(button)s", Ci.nsIPrefLocalizedString).data);
		key_%(num)s.setAttribute('modifiers', extensionPrefs.getComplexValue("modifier.%(button)s", Ci.nsIPrefLocalizedString).data);
	}
	keyset.appendChild(key_%(num)s);""" % {"num": i, "command": command, "button": button})
        with codecs.open(os.path.join(self._settings.get('button_sdk_root'), 'templates', 'keyset.js'), encoding='utf-8') as template_file:
            template = template_file.read()
        return template.replace('{{keys}}', '\n\t'.join(statements)).replace('{{pref_root}}', self._settings.get('pref_root'))
    
    def _jsm_create_menu(self, file_name, buttons):
        if not self._settings.get('menuitems'):
            return ''
        menu_id, menu_label, location = self._settings.get("menu_meta")
        statements = []
        data = self.create_menu_dom(file_name, buttons)
        in_submenu = {button: menuitem for button, menuitem in data.items() if menuitem.parent_id is None}
        in_menu = {button: menuitem for button, menuitem in data.items() if menuitem.parent_id is not None}
        num = 0
        meta = self._settings.get("file_to_menu").get(location, {}).get(file_name)
        if in_submenu and meta:
            with codecs.open(os.path.join(self._settings.get('button_sdk_root'),
                                          'templates', 'menu.js'), encoding='utf-8') as template_file:
                template = template_file.read()
            menu_name, insert_after = meta
            statements.append(template % {
                "menu_name": menu_name,
                "menu_id": menu_id,
                "label": menu_label,
                "class": "menu-iconic",
                "menu_label": menu_label,
                "insert_after": insert_after
            })
            num += 3
            for item, _, _ in in_submenu.values():
                item_statements, count, _ = self._create_dom(item, top="menupopup_2", count=num, doc="document")
                num = count + 1
                statements.extend(item_statements)
        for item, menu_name, insert_after in in_menu.values():
            statements.append("var menupopup_%s = document.getElementById('%s');" % (num, menu_name))
            var_name = "menupopup_%s" % num
            num += 1
            item.attrib["insertafter"] = insert_after
            item_statements, count, _ = self._create_dom(item, top=var_name, count=num)
            num = count + 1
            statements.extend(item_statements)
        return "\n\t".join(statements)
    
    def _dom_string_lookup(self, value):
        result = []
        items = re.findall(r'&.+?;|[^&;]+', value)
        for item in items:
            if item == "&brandShortName;":
                result.append("Cc['@mozilla.org/xre/app-info;1'].createInstance(Ci.nsIXULAppInfo).name")
            elif item[0] == '&' and item[-1] == ';':
                result.append("buttonStrings.get('%s')" % item[1:-1])
            else:
                result.append("'%s'" % item)
        return ' + '.join(result)

    def _create_dom(self, root, top=None, count=0, doc='document', child_parent=None, rename=None, append_children=True):
        num = count
        if rename == None:
            rename = {}
        children = []
        statements = [
            "var %s_%s = %s.createElement('%s');" % (root.tag, num, doc, rename.get(root.tag, root.tag)),
        ]
        for key, value in sorted(root.attrib.items(), key=self._attr_key):
            if key == 'id':
                if not self._settings.get("custom_button_mode"):
                    statements.append("%s_%s.id = '%s';" % (root.tag, num, value))
            elif key in ('label', 'tooltiptext') or (root.tag == 'key' and key in ('key', 'keycode', 'modifiers')):
                statements.append("%s_%s.setAttribute('%s', %s);" % ((root.tag, num, key, self._dom_string_lookup(value))))
            elif key == "class":
                for val in value.split():
                    statements.append('%s_%s.classList.add("%s");' % (root.tag, num, val))
            elif key[0:2] == 'on':
                if key == 'oncommand' and root.tag == 'key':
                    # we do this because key elements without a oncommand are optimized away
                    # but we can't call our function, because that might not exist 
                    # in the window scope, so the event listener has to be used
                    statements.append("%s_%s.setAttribute('oncommand', 'void(0);');" % (root.tag, num))
                if key == 'oncommand' and self._settings.get("custom_button_mode") and top == None:
                    self._command = value
                else:
                    statements.append("%s_%s.addEventListener('%s', function(event) {\n\t\t\t\t%s\n\t\t\t}, false);" % (root.tag, num, key[2:], self._patch_call(value)))
            elif key == "insertafter":
                pass
            elif key == "showamenu":
                statements.append("%s_%s.addEventListener('DOMMenuItemActive', toolbar_buttons.menuLoaderEvent, false);"  % (root.tag, num))
                statements.append("%s_%s._handelMenuLoaders = true;"  % (root.tag, num))
                statements.append("%s_%s.setAttribute('%s', '%s');" % ((root.tag, num, key, value)))
            elif key == "toolbarname":
                # this is just for our custom toolbars which are named "Toolbar Buttons 1" and the like
                name, sep, other = value.partition(' ')
                other = " + '%s%s'" % (sep, other) if sep else ""
                value = "buttonStrings.get('%s')%s" % (name, other)
                statements.append("%s_%s.setAttribute('%s', %s);" % ((root.tag, num, key, value)))
            elif key == "type" and value == "menu-button" and 'id' in root.attrib:
                statements.append('''if(extensionPrefs.getPrefType('menupopup.hide.{0}') == extensionPrefs.PREF_INVALID || !extensionPrefs.getBoolPref('menupopup.hide.{0}')) {{\n\t\t\t\t{1}_{2}.setAttribute("{3}", "{4}");\n\t\t\t}}'''.format(root.attrib['id'], root.tag, num, key, value))
            else:
                statements.append('%s_%s.setAttribute("%s", "%s");' % ((root.tag, num, key, value)))
        for node in root:
            sub_nodes, count, _ = self._create_dom(node, '%s_%s' % (root.tag, num), count+1, doc=doc, rename=rename, child_parent=(child_parent if top == None else None))
            if append_children:
                statements.extend(sub_nodes)
            else:
                children = sub_nodes
        if not top:
            statements.append('return %s_%s;' % (root.tag, num))
        else:
            if "insertafter" in root.attrib:
                statements.append("%s.insertBefore(%s_%s, %s.getElementById('%s').nextSibling);" % (top, root.tag, num, doc, root.attrib.get("insertafter")))
            else:
                statements.append('%s.appendChild(%s_%s);' % (top if not child_parent else child_parent, root.tag, num))
        return statements, count, children
    
    def _attr_key(self, attr):
        order = ('id', 'defaultarea', 'type', 'label', 'tooltiptext', 'command', 'onclick', 'oncommand')
        if attr[0].lower() in order:
            return order.index(attr[0].lower())
        return 100
        
    def _create_dom_button(self, button_id, root, file_name, count, toolbar_ids):
        add_to_main_toolbar = self._settings.get("add_to_main_toolbar")
        if 'viewid' in root.attrib:
            self._ui_ids.add(root.attrib["viewid"])
            statements, _, children = self._create_dom(root, child_parent="popupset", append_children=False)
            children[0] = """var popupset = document.getElementById('PanelUI-multiView');
				if(popupset) {
					var menupopup_1 = document.createElement('panelview');
				} else {
					var menupopup_1 = document.createElement('menupopup');
					popupset = document.documentElement;
				}"""
            data = {
                "type": "'view'",
                "onBeforeCreated": 'function (document) {\n\t\t\t\tvar window = document.defaultView;\n\t\t\t\t%s\n\t\t\t}' % "\n\t\t\t\t".join(children),
            }
        elif 'usepanelview' in root.attrib:
            self._ui_ids.add("%s-panel-view" % root.attrib["id"])
            statements, _, _ = self._create_dom(root)
            root_clone = deepcopy(root)
            if root.attrib['usepanelview'] == 'button-menu':
                del root_clone.attrib["type"]
                root_clone[0].insert(0, ET.Element("menuseparator"))
                root_clone[0].insert(0, ET.Element("menuitem", root_clone.attrib))
            for node in root_clone[0]:
                node.attrib['class'] = 'subviewbutton'
            _, _, children = self._create_dom(root_clone, child_parent="popupset", rename={'menuitem': 'toolbarbutton'}, append_children=False)
            children.pop(0)
            data = {
                "type": "'custom'",
                "onBuild": '''function (document) {
				var window = document.defaultView;
				var popupset = document.getElementById('PanelUI-multiView');
				if(popupset) {
					var menupopup_1 = document.createElement('panelview');
					%s
					menupopup_1.id = "%s-panel-view";
				}
				%s
		}''' % ("\n\t\t\t\t\t".join(children), root.attrib['id'], "\n\t\t\t\t".join(statements))
            }
        else:
            statements, _, _ = self._create_dom(root)
            data = {
                "type": "'custom'",
                "onBuild": 'function (document) {\n\t\t\t\tvar window = document.defaultView;\n\t\t\t\t%s\n\t\t\t}' % "\n\t\t\t\t".join(statements)
            }
        self._apply_toolbox(file_name, data)
        toolbar_max_count = self._settings.get("buttons_per_toolbar")
        if add_to_main_toolbar and button_id in add_to_main_toolbar:
            data['defaultArea'] = "'%s'" % self._settings.get('file_to_main_toolbar').get(file_name)
        elif self._settings.get("put_button_on_toolbar"):
            toolbar_index = count // toolbar_max_count
            if len(toolbar_ids) > toolbar_index:
                data['defaultArea'] = "'%s'" % toolbar_ids[toolbar_index]
        for key, value in root.attrib.items():
            if key in ('label', 'tooltiptext'):
                data[key] = self._dom_string_lookup(value)
            elif key == "id":
                data[key] = "'%s'" % value
            elif key == 'oncommand':
                self._button_commands[file_name][button_id] = value
            elif key == 'viewid':
                data["viewId"] = "'%s'" % value
            elif key == 'onviewshowing':
                data["onViewShowing"] = "function(event){\n\t\t\t\t%s\n\t\t\t}" % self._patch_call(value)
            elif key == 'onviewhideing':
                data["onViewHiding"] = "function(event){\n\t\t\t\t%s\n\t\t\t}" % self._patch_call(value)
        for js_file in self._get_js_file_list(file_name):
            if self._button_js_setup.get(js_file, {}).get(button_id):
                data["onCreated"] = "function(aNode){\n\t\t\tvar document = aNode.ownerDocument;\n\t\t\t%s\n\t\t}" % self._button_js_setup[js_file][button_id]
        items = sorted(data.items(), key=self._attr_key)
        return "\n\ttry{\n\t\tCustomizableUI.createWidget({\n\t\t\t%s\n\t\t});\n\t} catch(e) {}\n" % ",\n\t\t\t".join("%s: %s" % (key, value) for key, value in items)

    def _apply_toolbox(self, file_name, data):
        toolbox_info = self._settings.get("file_to_toolbar_box2").get(file_name)
        if toolbox_info:
            window_file, toolbox_id = toolbox_info
            data["toolbox"] = "'%s'" % toolbox_id
            if window_file:
                data["window"] = "'%s'" % window_file


    def _patch_call(self, value):
        data = []
        if re.search(r'\bthis\b', value):
            value = re.sub(r'\bthis\b', 'aThis', value)
            data.append("var aThis = event.currentTarget;")
        if re.search(r'\bdocument\b', value):
            data.append("var document = event.target.ownerDocument;")
        if re.search(r'\bwindow\b', value):
            data.append("var window = event.target.ownerDocument.defaultView;")
        data.append(value)
        return "\n\t\t\t\t".join(data)

    def _create_jsm_button(self, button_id, root, file_name, count, toolbar_ids):
        toolbar_max_count = self._settings.get("buttons_per_toolbar")
        add_to_main_toolbar = self._settings.get("add_to_main_toolbar")
        data = {}
        attr = root.attrib
        self._apply_toolbox(file_name, data)
        if add_to_main_toolbar and button_id in add_to_main_toolbar:
            data['defaultArea'] = "'%s'" % self._settings.get('file_to_main_toolbar').get(file_name)
        elif self._settings.get("put_button_on_toolbar"):
            toolbar_index = count // toolbar_max_count
            if len(toolbar_ids) > toolbar_index:
                data['defaultArea'] = "'%s'" % toolbar_ids[toolbar_index]
        for key, value in attr.items():
            if key in ('label', 'tooltiptext'):
                data[key] = self._dom_string_lookup(value)
            elif key == "id":
                data[key] = "'%s'" % value
            elif key in ('onclick', 'oncommand'):
                if key == 'oncommand':
                    self._button_commands[file_name][button_id] = value
                key = 'onCommand' if key == 'oncommand' else 'onClick'
                data[key] = "function(event) {\n\t\t\t\t%s\n\t\t\t}" % self._patch_call(value)
        for js_file in self._get_js_file_list(file_name):
            if self._button_js_setup.get(js_file, {}).get(button_id):
                data["onCreated"] = "function(aNode) {\n\t\t\t\tvar document = aNode.ownerDocument;\n\t\t\t\t%s\n\t\t\t}" % self._button_js_setup[js_file][button_id]
        items = sorted(data.items(), key=self._attr_key)
        result = "\n\ttry{\n\t\tCustomizableUI.createWidget({\n\t\t\t%s\n\t\t});\n\t} catch(e) {}\n" % ",\n\t\t\t".join("%s: %s" % (key, value) for (key, value) in items)
        return result

    def get_jsm_files(self):
        with codecs.open(os.path.join(self._settings.get('button_sdk_root'), 'templates', 'button.jsm'), encoding='utf-8') as template_file:
            template = template_file.read()
        result = {}
        simple_attrs = {'label', 'tooltiptext', 'id', 'oncommand', 'onclick', 'key', 'class'}
        button_hash, toolbar_template = self._get_toolbar_info()
        for file_name, values in self._button_xul.items():
            jsm_file = []
            js_includes = []
            for js_file in self._get_js_file_list(file_name):
                if js_file != "loader" and js_file in self._included_js_files:
                    js_includes.append("""loader.loadSubScript("chrome://%s/content/%s.js", gScope);""" % (self._settings.get("chrome_name"), js_file))
            toolbars, toolbar_ids = self._create_jsm_toolbar(button_hash, toolbar_template, file_name, values)
            count = 0
            modules = set()
            for button_id, xul in values.items():
                root = ET.fromstring(xul.replace('&', '&amp;'))
                modules.update(self._modules[button_id])
                attr = root.attrib
                if not len(root) and not set(attr.keys()).difference(simple_attrs) and (not "class" in attr or attr["class"] == "toolbarbutton-1 chromeclass-toolbar-additional"):
                    jsm_file.append(self._create_jsm_button(button_id, root, file_name, count, toolbar_ids))
                else:
                    jsm_file.append(self._create_dom_button(button_id, root, file_name, count, toolbar_ids))
                count += 1
            modules_import = "\n" + "\n".join("try { Cu.import('%s'); } catch(e) {}" % mod for mod in modules if mod)
            if self._settings.get("menu_meta"):
                menu_id, menu_label, _ = self._settings.get("menu_meta")
            else:
                menu_id, menu_label = "", ""
            end = set()
            menu = self._jsm_create_menu(file_name, values)
            for js_file in set(self._get_js_file_list(file_name) + [file_name]):
                if self._button_js_setup.get(js_file, {}):
                    end.update(self._button_js_setup[js_file].values())
            if self._settings.get("menuitems") and menu:
                end.add("toolbar_buttons.setUpMenuShower(document);")
            result[file_name] = (template.replace('{{locale-file-prefix}}', self._settings.get("locale_file_prefix"))
                        .replace('{{modules}}', modules_import)
                        .replace('{{scripts}}', "\n\t".join(js_includes))
                        .replace('{{button_ids}}', json.dumps(list(values.keys()))) # we use this not self._buttons, because of the possible generated toolbar toggle buttons
                        .replace('{{toolbar_ids}}', json.dumps(toolbar_ids))
                        .replace('{{toolbars}}', toolbars)
                        .replace('{{menu_id}}', menu_id)
                        .replace('{{ui_ids}}', json.dumps(list(self._ui_ids)))
                        .replace('{{toolbox}}', self._settings.get("file_to_toolbar_box").get(file_name, ('', ''))[1])
                        .replace('{{menu}}', menu)
                        .replace('{{keys}}', self.jsm_keyboard_shortcuts(file_name))
                        .replace('{{end}}', "\n\t".join(end))
                        .replace('{{buttons}}', "\n\n".join(jsm_file))
                        .replace('{{pref_root}}', self._settings.get("pref_root"))
                        .replace('{{chrome_name}}', self._settings.get("chrome_name")))
        return result
    
    def _create_jsm_toolbar(self, button_hash, toolbar_template, file_name, values):
        toolbar_ids = []
        toolbars = []
        if file_name in self._settings.get("extra_toolbars_disabled"):
            return '', []
        count = 0
        max_count = self._settings.get("buttons_per_toolbar")
        buttons = list(values.keys())
        for box_setting, include_setting in [("file_to_toolbar_box", "include_toolbars"),
                                                       ("file_to_bottom_box", "include_satusbars")]:
            toolbar_node, toolbar_box = self._settings.get(box_setting).get(file_name, ('', ''))
            data = {
                "defaultset": "",
                "persist": "collapsed,hidden",
                "context": "toolbar-context-menu",
                "class": "toolbar-buttons-toolbar chromeclass-toolbar",
                "mode": "icons",
                "iconsize": "small",
                "customizable": "true",
            }
            if self._settings.get(include_setting) and toolbar_box:
                number = self.toolbar_count(include_setting, values, max_count)
                for i in range(number):
                    if self._settings.get("put_button_on_toolbar"):
                        data["defaultset"] = ",".join(buttons[i * max_count:(i + 1) * max_count])
                    button_hash.update(bytes(i))
                    hash = button_hash.hexdigest()[:6]
                    label_number = "" if (number + count) == 1 else " %s" % (i + count + 1)
                    toolbar_ids.append("tb-toolbar-%s" % hash)
                    if include_setting != "include_toolbars":
                        data["toolboxid"] = toolbar_box
                    data["id"] = "tb-toolbar-%s" % hash
                    toolbarname = self._dom_string_lookup("&tb-toolbar-buttons-toggle-toolbar.name;%s" % label_number)
                    values["tb-toolbar-buttons-toggle-toolbar-%s" % hash] = toolbar_template.replace("{{hash}}", hash).replace("{{ number }}", label_number)
                    toolbars.append("""createToolbar(document, '%s', %s, %s)""" % (toolbar_box, json.dumps(data), toolbarname))
                count += number
        return "\n\t\t".join(toolbars), toolbar_ids
