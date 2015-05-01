import os
import re
import io
import math
import hashlib
import codecs
from collections import defaultdict
from builder import grayscale
from builder.util import get_pref_folders
from collections import namedtuple
import lxml.etree as ET
try:
    from PIL import Image
except ImportError:
    pass
from builder.simple_button import SimpleButton, get_image

try:
    basestring
except NameError:
    basestring = str #py3

Menuitem = namedtuple('Menuitem', ['node', 'parent_id', 'insert_after'])

class Button(SimpleButton):
    def __init__(self, folders, buttons, settings, applications):
        self._suported_applications = set()
        self._button_files = set()
        self._button_xul = defaultdict(dict)

        super(Button, self).__init__(folders, buttons, settings, applications)

        self._button_js = defaultdict(dict)
        self._properties_strings = set()
        self._preferences = {}
        self._button_options = {}
        self._button_options_js = {}
        self._application_button_options = defaultdict(dict)
        self._option_applications = set()
        self._has_javascript = False
        self._manifest = []
        self._extra_files = {}
        self._res = {}
        self._pref_list = defaultdict(list)
        self._button_style = {}
        self._option_titles = set()
        self._option_icons = set()
        self._modules = defaultdict(set)
        self._button_js_setup = defaultdict(dict)
        self._button_commands = defaultdict(dict)

        # we always want these file
        self._button_js["loader"]["_"] = ""
        self._button_js["button"]["_"] = ""
        self._included_js_files = []

        for folder, button, files in self._info:
            for file_name in (self._window_files + self._app_files):
                js_file = file_name + ".js"
                if (file_name == "button"
                         or set(self._settings.get("file_to_application").get(file_name, [])
                                   ).intersection(self._applications)):
                    if js_file in files:
                        with open(os.path.join(folder, js_file)) as js:
                            self._button_js[file_name][button] = js.read()
                    if self._settings.get("extended_buttons") and ("extended_%s" % js_file) in files:
                        with open(os.path.join(folder, "extended_%s" % js_file)) as js:
                            self._button_js[file_name][button] = js.read()

            if button in self._settings.get("keyboard_custom_keys"):
                self._button_keys[button].update(self._settings.get("keyboard_custom_keys")[button])

            if "preferences" in files:
                with open(os.path.join(folder, "preferences"), "r") as preferences:
                    for line in preferences:
                        name, value = line.split(":", 1)
                        self._preferences[name] = value.strip()
                        self._pref_list[name].append(button)
            if "manifest" in files:
                with open(os.path.join(folder, "manifest"), "r") as manifest:
                    self._manifest.append(manifest.read())
            if "option.xul" in files:
                with open(os.path.join(folder, "option.xul"), "r") as option:
                    self._button_options[button] = (option.readline(), option.read())
            if self._settings.get("extra_options") and "extended_option.xul" in files:
                with open(os.path.join(folder, "extended_option.xul"), "r") as option:
                    self._button_options[button] = (option.readline(), option.read())
            for file_name in files:
                if file_name.endswith('_option.xul'):
                    application = file_name[0:-11]
                    if application in self._settings.get("applications_data"):
                        with open(os.path.join(folder, file_name), "r") as option:
                            self._application_button_options[button][application] = (option.readline(), option.read())
            if "option.js" in files:
                with open(os.path.join(folder, "option.js"), "r") as option:
                    self._button_options_js[button] = option.read()
            if "files" in files:
                for file in os.listdir(os.path.join(folder, "files")):
                    if file[0] != ".":
                        self._extra_files[file] = os.path.join(folder, "files", file)
            if "file_list" in files:
                with open(os.path.join(folder, "file_list"), "r") as file_list:
                    for file in file_list:
                        if file.strip():
                            self._extra_files[file.strip()] = os.path.join(self._settings.get("project_root"), "files", file.strip())
            if "res" in files:
                for file in os.listdir(os.path.join(folder, "res")):
                    if file[0] != ".":
                        self._res[file] = os.path.join(folder, "res", file)
            if "res_list" in files:
                with open(os.path.join(folder, "res_list"), "r") as res_list:
                    for file in res_list:
                        if file.strip():
                            self._res[file.strip()] = os.path.join(self._settings.get("project_root"), "files", file.strip())
            if "style.css" in files:
                with open(os.path.join(folder, "style.css"), "r") as style:
                    self._button_style[button] = style.read()
            if "modules" in files:
                with open(os.path.join(folder, "modules"), "r") as modules:
                    self._modules[button].update(line.strip() for line in modules)

    def get_suported_applications(self):
        return self._suported_applications

    def get_button_xul(self):
        return self._button_xul

    def get_extra_files(self):
        return self._extra_files

    def get_resource_files(self):
        return self._res
    
    def get_description(self, button):
        folder = self._button_folders[button]
        with open(os.path.join(folder, "description"), "r") as description:
            return description.read()
        return ""

    def _process_xul_file(self, folder, button, xul_file, file_name):
        application = SimpleButton._process_xul_file(self, folder, button, xul_file, file_name)
        if xul_file != "%s.xul" % file_name and self._button_xul.get(file_name, {}).get(button):
            return
        self._suported_applications.update(set(application).intersection(self._applications))
        self._button_files.add(file_name)
        with open(os.path.join(folder, xul_file)) as xul:
            self._button_xul[file_name][button] = xul.read().strip()

    def get_manifest(self):
        return "\n".join(self._manifest)

    def get_options(self):
        result = {}
        if self._button_options_js:
            javascript = ("""<script type="application/x-javascript" src="chrome://%s/content/loader.js"/>\n"""
                          """<script type="application/x-javascript" src="chrome://%s/content/button.js"/>\n"""
                          """<script type="application/x-javascript" src="chrome://%s/content/option.js"/>\n"""
                          % (self._settings.get("chrome_name"), self._settings.get("chrome_name"),
                             self._settings.get("chrome_name")))
        else:
            javascript = ""
        with open(os.path.join(self._settings.get('button_sdk_root'), "templates", "option.xul"), "r") as overlay_window_file:
            overlay_window = (overlay_window_file.read()
                       .replace("{{chrome_name}}", self._settings.get("chrome_name"))
                       .replace("{{locale_file_prefix}}", self._settings.get("locale_file_prefix"))
                       .replace("{{javascript}}", javascript))
        if self._settings.get("menuitems"):
            with open(os.path.join(self._settings.get('button_sdk_root'), "templates", "showmenu-option.xul"), "r") as menu_option_file:
                menu_option_tempate = menu_option_file.read() 
            if self._settings.get("menu_placement") is None and self._settings.get("menu_meta"):
                menu_id, menu_label, location = self._settings.get("menu_meta")
                self._button_options[menu_id] = ("tb-show-a-menu.option.title:menu.png", 
                        menu_option_tempate.replace("{{menu_id}}", menu_id).replace("{{menu_label}}", menu_label))
                self._button_applications[menu_id] = self._applications
            else:
                for button in self._buttons:
                    self._button_options["%s-menu-item" % button] = ("tb-show-a-menu.option.title:menu.png", 
                        menu_option_tempate.replace("{{menu_id}}", "%s-menu-item" % button).replace("{{menu_label}}", "%s.label" % button))
                    self._button_applications["%s-menu-item" % button] = self._applications
        files = defaultdict(dict)
        def append(files, application, first, data):
            meta = first.strip().split(':')
            if len(meta) == 2:
                title, icon = meta
            else:
                title, icon, appslist = meta
                if application not in appslist.split():
                    return
            if title in files[application]:
                files[application][title]['data'].append(data)
            else:
                files[application][title] = {'data': [data], 'icon': icon}
        for button, (first, data) in self._button_options.items():
            for application in self._button_applications[button]:
                self._option_applications.add(application)
                append(files, application, first, data.replace("{{pref_root}}", self._settings.get("pref_root")))
        for button, items in self._application_button_options.items():
            for application, (first, data) in items.items():
                append(files, application, first, data.replace("{{pref_root}}", self._settings.get("pref_root")))
        if self._pref_list:
            limit = ".xul,".join(self._pref_list.keys()) + ".xul"
            pref_files = get_pref_folders(limit, self._settings)
            for file_name, name in zip(*pref_files):
                data_fp = open(file_name, "r")
                first = data_fp.readline()
                data = data_fp.read()
                data_fp.close()
                applications = set()
                for button in self._pref_list[name[:-4]]:
                    for application in self._button_applications[button]:
                        self._option_applications.add(application)
                        applications.add(application)
                    self._button_options[file_name] = (first, data)
                for application in applications:
                    append(files, application, first, data.replace("{{pref_root}}", self._settings.get("pref_root")))
        for application, data in files.items():
            button_pref = []
            for panel, info in data.items():
                icon = info['icon']
                self._option_icons.add(icon)
                self._option_titles.add(panel)
                data = "\n\t\t\t\t".join("\n".join(info['data']).split("\n"))
                panel_xml = """\t\t\t<prefpane id="prefpane-%s" image="chrome://%s/skin/option/%s" label="&%s;" style="max-height:400px;" flex="1"><vbox flex="1" style="overflow:auto;">%s</vbox></prefpane>"""  % (
                                    panel.replace('.', '-'), self._settings.get("chrome_name"), icon, panel, data)
                button_pref.append(panel_xml)
            result["%s-options" % application] = overlay_window.replace("{{options}}",
                                    "\n".join(button_pref))
        return result

    def get_options_applications(self):
        """Returns a list of applications with options

        precondition: get_options() has been called
        """
        return self._option_applications

    def get_option_icons(self):
        """Returns a list of icons used by the options window

        precondition: get_options() has been called
        """
        return self._option_icons
        
    def get_file_names(self):
        return self._button_files

    def get_locale_strings(self):
        locale_match = re.compile("&([a-zA-Z0-9.-]*);")
        strings = []
        for buttons in self._button_xul.values():
            for button in buttons.values():
                strings.extend(locale_match.findall(button))
        for button in self._button_keys.keys():
            strings.extend(["%s.key" % button, "%s.modifier" % button])
        strings = list(set(strings))
        strings.sort()
        return strings
    
    def get_extra_locale_strings(self):
        locale_match = re.compile("&([a-zA-Z0-9.-]*);")
        strings = []
        for file_name in self._extra_files.values():
            with open(file_name, 'r') as xul:
                strings.extend(locale_match.findall(xul.read()))
        strings = list(set(strings))
        strings.sort()
        return strings

    def get_options_strings(self):
        """Returns a list of strings used by the options window

        precondition: get_options() has been called
        """
        locale_match = re.compile("&([a-zA-Z0-9.-]*);")
        strings = list(self._option_titles)
        strings.append("options.window.title")
        for first, value in self._button_options.values():
            strings.extend(locale_match.findall(value))
        return list(set(strings))

    def get_defaults(self, format_dict=False):
        settings = []
        if self._settings.get("translate_description"):
            settings.append(("extensions.%s.description" % self._settings.get("extension_id"), 
                         """'chrome://%s/locale/%sbutton.properties'""" % (self._settings.get("chrome_name"), self._settings.get("locale_file_prefix"))))
        if self._settings.get("show_updated_prompt") or self._settings.get("add_to_main_toolbar"):
            settings.append(("%s%s" % (self._settings.get("pref_root"), self._settings.get("current_version_pref")), "''"))
        if self._settings.get("menuitems"):
            if self._settings.get("as_submenu") and self._settings.get("menu_meta"):
                menu_id, menu_label, location = self._settings.get("menu_meta")
                settings.append(("%sshowamenu.%s" % (self._settings.get("pref_root"), menu_id), self._settings.get("default_show_menu_pref")))
            else:
                for button in self._buttons:
                    settings.append(("%sshowamenu.%s-menu-item" % (self._settings.get("pref_root"), button), self._settings.get("default_show_menu_pref")))
        for name, value in self._preferences.items():
            settings.append(("%s%s" % (self._settings.get("pref_root"), name), value))
        if format_dict:
            return "\n\t".join("%s: %s," % setting for setting in settings)
        else:
            return "\n".join("pref('%s', %s);" % setting for setting in settings)
    
    def get_icon_size(self):
        small, large = self._settings.get("icon_size")
        icon_size = {
            "small": small,
            "large": large,
        }
        if self._settings.get("include_icons_for_custom_window") and "32" not in self._settings.get("icon_size"):
            icon_size["window"] = "32"
        elif "32" in self._settings.get("icon_size"):
            icon_size["window"] = "32"
        else:
            icon_size["window"] = small if int(small) >= 32 else large
        if self._settings.get('menuitems'):
            icon_size["menu"] = "16"
        return icon_size

    def get_css_file(self, toolbars=None):
        image_list = []
        image_datas = {}
        style_file = os.path.join(self._settings.get("project_root"), "files", "button.css")
        if not os.path.isfile(style_file):
            style_file = os.path.join(self._settings.get('button_sdk_root'), "templates", "button.css")
        with codecs.open(style_file,"r", encoding='utf-8') as f:
            template = f.read()
        lines = [template]
        values = {"chrome_name": self._settings.get("chrome_name")}
        icon_sizes = self.get_icon_size()
        icon_size_set = set(icon_sizes.values())
        image_map = {}
        if self._settings.get("merge_images"):
            image_set = list()
            for button, image_data in self._button_image.items():
                for image, modifier in image_data:
                    image_set.append(image)
            image_count = len(image_set)
            image_map_size = {}
            image_map_x = {}
            for size in icon_size_set:
                if size is not None:
                    y, x = int(math.ceil(image_count*int(size) / 1000.0)), (1000 // int(size))
                    if y == 1:
                        x = image_count
                    image_map_x[size] = x
                    image_map_size[size] = Image.new("RGBA", (x * int(size), y * int(size)), (0, 0, 0, 0))
        count = 0
        offset = 0
        def box_cmp(x, offset):
            y_offset = offset // x
            x_offset = offset % x
            return (x_offset * int(size), y_offset * int(size), (x_offset + 1) * int(size), (y_offset + 1) * int(size))
        for button, image_data in self._button_image.items():
            values["id"] = button
            for image, modifier in image_data:
                if image[0] == "*" or image[0] == "-":
                    name = list(image[1:].rpartition('.'))
                    name.insert(1, "-disabled")
                    _image = "".join(name)
                    opacity = 1.0 if image[0] == "-" else 0.9
                    
                    try:
                        data = {}
                        for size in icon_size_set:
                            if size is not None:
                                data[size] = grayscale.image_to_graysacle(get_image(self._settings, size, image[1:]), opacity)
                    except ValueError:
                        print("image %s does not exist" % image)
                        continue
                    if self._settings.get("merge_images"):
                        if image_map.get(_image):
                            offset = image_map.get(_image)
                        else:
                            offset = count
                            image_map[_image] = offset
                            image_map = {}
                            for size in icon_size_set:
                                if size is not None:
                                    image_map_size[size].paste(Image.open(io.BytesIO(data[size])), box_cmp(image_map_x[size], offset))
                            count += 1
                    else:
                        offset = count
                        for size in icon_size_set:
                            if size is not None:                            
                                image_datas[os.path.join("skin", size, _image)] = data[size]
                        count += 1
                    image = _image
                else:
                    if self._settings.get("merge_images"):
                        if image_map.get(image):
                            offset = image_map.get(image)
                        else:
                            try:
                                offset = count
                                image_map[image] = offset
                                for size in icon_size_set:
                                    if size is not None:
                                        im = Image.open(get_image(self._settings, size, image))
                                        image_map_size[size].paste(im, box_cmp(image_map_x[size], offset))
                                count += 1
                            except IOError:
                                print("image %s does not exist" % image)
                            except ValueError as e:
                                print("count not use image: %s" % image)
                    else:
                        offset = count
                        image_list.append(image)
                        count += 1
                selectors = dict((key, list()) for key in icon_size_set)
                for name, size in icon_sizes.items():
                    if size is None:
                        continue
                    if name == "small":
                        selectors[size].append("toolbar[iconsize='small'] toolbarbutton#%s%s" % (button, modifier))
                    elif name == "large":
                        selectors[size].append("toolbar toolbarbutton#%s%s" % (button, modifier))
                    elif name == "menu":
                        selectors[size].append("menu#%s-menu-item%s" % (button, modifier))
                        selectors[size].append("menuitem#%s-menu-item%s" % (button, modifier))
                    elif name == "window":
                        selectors[size].append("toolbarbutton#%s%s" % (button, modifier))
                if self._settings.get("merge_images"):
                    for size in icon_size_set:
                        if size is not None:
                            values["size"] = size        
                            values["selectors"] = ", ".join(selectors[size])
                            left, top, right, bottom = box_cmp(image_map_x[size], offset)
                            values.update({"top": top, "left": left, "bottom": bottom, "right": right})
                            lines.append("""%(selectors)s {"""
                                     """\n\tlist-style-image:url("chrome://%(chrome_name)s/skin/%(size)s/button.png");"""
                                     """\n\t-moz-image-region: rect(%(top)spx %(right)spx %(bottom)spx %(left)spx);\n}""" % values)
                else:
                    values["image"] = image
                    for size in icon_size_set:
                        if size is not None:
                            values["size"] = size
                            values["selectors"] = ", ".join(selectors[size])   
                            lines.append("""%(selectors)s {\n\tlist-style-image:url("chrome://%(chrome_name)s/skin/%(size)s/%(image)s");"""
                                     """\n\t-moz-image-region: rect(0px %(size)spx %(size)spx 0px);\n}""" % values)
        if self._settings.get("merge_images"):
            for size in icon_size_set:
                if size is not None:
                    size_io = io.BytesIO()
                    image_map_size[size].save(size_io, "png")
                    image_datas[os.path.join("skin", size, "button.png")] = size_io.getvalue()
                    size_io.close()
        if self._settings.get("include_toolbars"):
            image_list.append("toolbar-button.png")
            for name, selector in (('small', "toolbar[iconsize='small'] .toolbar-buttons-toolbar-toggle"), 
                                   ('large', 'toolbar .toolbar-buttons-toolbar-toggle'), 
                                   ('window', '.toolbar-buttons-toolbar-toggle')):
                if icon_sizes[name] is not None:
                    lines.append(('''%(selector)s {'''
                    '''\n\tlist-style-image:url("chrome://%(chrome_name)s/skin/%(size)s/toolbar-button.png");'''
                    '''\n}''') % {"size": icon_sizes[name], "selector": selector,
                       "chrome_name": self._settings.get("chrome_name")})
        for item in set(self._button_style.values()):
            lines.append(item)
        return "\n".join(lines), image_list, image_datas

    def get_js_files(self):
       
        interface_match = re.compile("(?<=toolbar_buttons.interfaces.)[a-zA-Z]*")
        function_match = re.compile("^[a-zA-Z0-9_]*\s*:\s*"
                                    "(?:function\([^\)]*\)\s*)?{.*?^}[^\n]*",
                                    re.MULTILINE | re.DOTALL)
        function_name_match = re.compile("((^[a-zA-Z0-9_]*)\s*:\s*"
                                         "(?:function\s*\([^\)]*\)\s*)?{.*?^})",
                                          re.MULTILINE | re.DOTALL)
        include_match = re.compile("(?<=^#include )[a-zA-Z0-9_]*",
                                   re.MULTILINE)
        include_match_replace = re.compile("^#include [a-zA-Z0-9_]*\n?",
                                           re.MULTILINE)
        detect_depandancy = re.compile("(?<=toolbar_buttons.)[a-zA-Z]*")
        string_match = re.compile("StringFromName\(\"([a-zA-Z0-9.-]*?)\"")

        multi_line_replace = re.compile("\n{2,}")
        js_files = defaultdict(str)
        js_includes = set()
        js_options_include = set()
        js_imports = set()
        
        # we look though the XUL for functions first
        for file_name, values in self._button_xul.items():
            for button, xul in values.items():
                js_imports.update(detect_depandancy.findall(xul))
        if self._settings.get("menuitems"):
            js_imports.add("sortMenu")
            js_imports.add("handelMenuLoaders")
            js_imports.add("setUpMenuShower")
        
        for file_name, js in self._button_js.items():
            js_file = "\n".join(js.values())
            js_includes.update(include_match.findall(js_file))
            js_file = include_match_replace.sub("", js_file)
            js_functions = function_match.findall(js_file)
            js_imports.update(detect_depandancy.findall(js_file))
            if js_functions:
                js_functions.sort(key=lambda x: x.lower())
                js_files[file_name] = "\t" + "\n\t".join(
                        ",\n".join(js_functions).split("\n"))
            for button_id, value in js.items():
                value = multi_line_replace.sub("\n", function_match.sub("", value).strip())
                if value:
                    self._button_js_setup[file_name][button_id] = value
            if self._settings.get("menuitems"):
                self._button_js_setup[file_name]["_menu_hider"] = "toolbar_buttons.setUpMenuShower(document);"
        shared = []
        lib_folder = os.path.join(self._settings.get("project_root"), "files", "lib")
        for file_name in os.listdir(lib_folder):
            with open(os.path.join(lib_folder, file_name), "r") as shared_functions_file:
                shared.append(shared_functions_file.read())
        shared_functions = "\n\n".join(shared)
        externals = dict((name, function) for function, name
                         in function_name_match.findall(shared_functions))
        if self._settings.get("include_toolbars"):
            js_imports.add("toggleToolbar")
        extra_functions = []
        js_imports.update(js_includes)
        loop_imports = js_imports
        while loop_imports:
            new_extra = [externals[func_name] for func_name in loop_imports
                           if func_name in js_imports if func_name in externals]
            extra_functions.extend(new_extra)
            new_imports = set(detect_depandancy.findall("\n".join(new_extra)))
            loop_imports = new_imports.difference(js_imports)
            js_imports.update(loop_imports)

        js_extra_file = "\n\t".join(",\n".join(extra_functions).split("\n"))
        if js_files.get("button"):
            js_files["button"] += ",\n\t" + js_extra_file
        elif js_extra_file:
            js_files["button"] += js_extra_file
        if not self._settings.get("custom_button_mode"):
            for file_name, data in js_files.items():
                if data:
                    js_files[file_name] = "toolbar_buttons.toolbar_button_loader(toolbar_buttons, {\n\t%s\n});\n" % data
            if not self._settings.get("restartless"):
                for file_name, data in self._button_js_setup.items():
                    end = """\nwindow.addEventListener("load", function toolbarButtonsOnLoad() {\n\twindow.removeEventListener("load", toolbarButtonsOnLoad, false);\n\t%s\n}, false);""" % "\n\t".join(data.values())
                    if file_name in js_files:
                        js_files[file_name] += end
                    else:
                        js_files[file_name] = end
        if self._button_options_js:
            extra_javascript = []
            for button, value in self._button_options_js.items():
                #TODO: dependency resolution is not enabled here yet
                js_options_include.update(include_match.findall(value))
                js_options_include.update(detect_depandancy.findall(self._button_options[button][1]))
                value = include_match_replace.sub("", value)
                js_functions = function_match.findall(value)
                self._button_options_js[button] = ",\n".join(js_functions)
                extra_javascript.append(multi_line_replace.sub("\n",
                                        function_match.sub("", value).strip()));
            self._button_options_js.update(dict((name, function) for function, name
                               in function_name_match.findall(shared_functions)
                               if name in js_options_include))
            with open(os.path.join(self._settings.get('button_sdk_root'), "templates", "option.js")) as option_fp:
                js_files["option"] = (option_fp.read()
                    % ("\n\t".join(",\n".join(val for val in self._button_options_js.values() if val).split("\n")), "\n".join(extra_javascript)))
        if (self._settings.get("show_updated_prompt") or self._settings.get("add_to_main_toolbar")) and not self._settings.get('restartless'):
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
        inerface_file = os.path.join(self._settings.get('project_root'), 'files', 'interfaces')
        if not os.path.isfile(inerface_file):
            inerface_file = os.path.join(self._settings.get('button_sdk_root'), 'templates', 'interfaces')
        interfaces = {}
        with open(inerface_file, "r") as interfaces_data:
            for line in interfaces_data:
                name, _ = line.split(":")
                interfaces[name] = line.strip()
        js_global_interfaces = set(interface_match.findall(js_files["button"]))
        for js_file, js_data in js_files.items():
            self._properties_strings.update(string_match.findall(js_data))
            js_interfaces = set(interface_match.findall(js_data))
            if js_interfaces:
                lines = []
                interfaces_list = sorted(interfaces.items(), key=lambda x: x[0].lower())
                for interface, constructor in interfaces_list:
                    if (interface in js_interfaces
                        and (interface not in js_global_interfaces
                             or js_file == "button")):
                        lines.append(constructor)
                if lines:
                    if not self._settings.get("custom_button_mode"):
                        js_files[js_file] = ("toolbar_buttons.toolbar_button_loader("
                                       "toolbar_buttons.interfaces, {\n\t%s\n});\n%s"
                                     % (",\n\t".join(lines).replace("{{pref_root}}", self._settings.get("pref_root")), js_files[js_file]))
                    else:
                        self._interfaces[js_file] = ",\n\t".join(lines)
            js_files[js_file] = js_files[js_file].replace("{{chrome_name}}",
                    self._settings.get("chrome_name")).replace("{{pref_root}}",
                    self._settings.get("pref_root")).replace("{{locale_file_prefix}}",
                    self._settings.get("locale_file_prefix"))
        js_files = dict((key, value) for key, value in js_files.items() if value)
        if js_files:
            self._has_javascript = True
            with open(os.path.join(self._settings.get('button_sdk_root'), "templates", "loader.js"), "r") as loader:
                js_files["loader"] = loader.read()
        self._included_js_files = js_files.keys()
        return js_files

    def get_properties_strings(self):
        """Returns the .properties strings used by the buttons.

        Precondition: get_js_files() has been called
        """
        return self._properties_strings

    def get_keyboard_shortcuts(self, file_name):
        if not self._settings.get("use_keyboard_shortcuts") or not self._settings.get("file_to_keyset").get(file_name):
            return ""
        keys = []
        for button, (key, modifier) in self._button_keys.items():
            attr = 'key' if len(key) == 1 else "keycode"
            if file_name in self._button_xul:
                mod = "" if not modifier else 'modifiers="&%s.modifier;" ' % button
                command = self._button_commands.get(file_name, {}).get(button)
                if command:
                    keys.append("""<key %s="&%s.key;" %sid="%s-key" oncommand="%s" />""" % (attr, button, mod, button, command))
                else:
                    if self._settings.get("menuitems"):
                        keys.append("""<key %s="&%s.key;" %sid="%s-key" command="%s-menu-item" />""" % (attr, button, mod, button, button))
                    else:
                        keys.append("""<key %s="&%s.key;" %sid="%s-key" command="%s" />""" % (attr, button, mod, button, button))
        if keys:
            return """\n <keyset id="%s">\n\t%s\n </keyset>""" % (self._settings.get("file_to_keyset").get(file_name), "\n\t".join(keys))
        else:
            return ""

    def create_menu_dom(self, file_name, buttons):
        data = {}
        menuitems = self._settings.get("menuitems")
        menu_placement = self._menu_placement(file_name, buttons)
        for button_id, xul in buttons.items():
            if not menuitems or button_id not in menuitems or button_id not in menu_placement:
                continue
            root = ET.fromstring(xul.replace('&', '&amp;'))
            root.tag = 'menu' if len(root) else 'menuitem'
            root.attrib['id'] = "%s-menu-item" % button_id
            root.attrib['class'] = "menu-iconic menuitem-iconic %s" % (root.attrib.get('class')
                        .replace('toolbarbutton-1 chromeclass-toolbar-additional', ''))
            if not len(root) and "toolbar_buttons.showAMenu" in root.attrib.get('oncommand', ''):
                root.attrib["showamenu"] = "true"
                ET.SubElement(root, "menupopup")
            if self._settings.get("use_keyboard_shortcuts") and button_id in self._button_keys:
                root.attrib['key'] = "%s-key" % button_id
            if root.attrib.get("type") == "menu-button" and len(root):
                root[0].insert(0, ET.Element("menuseparator"))
                root[0].insert(0, ET.Element("menuitem", root.attrib))
            root.attrib.pop("type", None)
            root.attrib.pop("tooltiptext", None)
            placement = menu_placement.get(button_id)
            if placement:
                data[button_id] = Menuitem(root, *placement)
            else:
                data[button_id] = Menuitem(root, None, None)
        return data

    def _list_has_str(self, lst, text):
        for item in lst:
            if text in item:
                return True
        return False
    
    def _menu_placement(self, file_name, buttons):
        menu_placement = self._settings.get("menu_placement")
        file_to_menu = self._settings.get("file_to_menu")
        if menu_placement is None:
            result = {button: None for button in buttons}
        elif isinstance(menu_placement, basestring):
            placement = file_to_menu.get(menu_placement).get(file_name)
            if placement is None:
                result = {}
            else:
                result = {button: placement for button in buttons}
        elif isinstance(menu_placement, dict):
            result = {button: file_to_menu.get(menu_placement.get(button), {}).get(file_name)
                      for button in buttons if button in menu_placement}
        else:
            result = {button: menu_placement for button in buttons}
        return result

    def toolbar_count(self, include_setting, values, max_count):
        number = self._settings.get(include_setting)
        if number == -1:
            number = int(math.ceil(float(len(values)) / max_count))
        return number

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
                    hash = button_hash.hexdigest()[:6]
                    label_number = "" if (number + count) == 1 else " %s" % (i + count + 1)
                    toolbar_ids.append("tb-toolbar-%s" % hash)
                    toolbar_box_id = "" if include_setting == "include_toolbars" else 'toolboxid="%s" ' % toolbar_box
                    toolbars.append('''<toolbar %spersist="collapsed,hidden" context="toolbar-context-menu" class="toolbar-buttons-toolbar chromeclass-toolbar" id="tb-toolbar-%s" mode="icons" iconsize="small" customizable="true" %s toolbarname="&tb-toolbar-buttons-toggle-toolbar.name;%s"/>''' % (toolbar_box_id, hash, defaultset, label_number))
                    values["tb-toolbar-buttons-toggle-toolbar-%s" % hash] = toolbar_template.replace("{{hash}}", hash).replace("{{ number }}", label_number)
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
        

    def _get_toolbar_info(self):
        button_hash = None
        toolbar_template = None
        if self._settings.get("include_toolbars") or self._settings.get("include_satusbars"):
            with codecs.open(os.path.join(self._settings.get('button_sdk_root'), 'templates', 'toolbar-toggle.xul'), encoding='utf-8') as template_file:
                toolbar_template = template_file.read()
            button_hash = hashlib.md5(self._settings.get('extension_id').encode('utf-8'))
        return button_hash, toolbar_template

    def _get_js_file_list(self, file_name):
        group_files = self._settings.get("file_map_keys")
        js_files = []
        for group_file in group_files:
            if self._has_javascript and group_file in self._button_js and file_name in self._settings.get("file_map")[group_file]:
                js_files.append(group_file)
        if  self._has_javascript and file_name in self._button_js and file_name not in js_files:
            js_files.append(file_name)
        return js_files
