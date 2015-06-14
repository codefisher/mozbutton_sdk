import os
import re
import io
import math
import hashlib
import codecs
from collections import defaultdict
from itertools import chain
from builder import grayscale
from builder.util import get_pref_folders
from collections import namedtuple
import lxml.etree as ET
from jinja2 import FileSystemLoader, Environment

try:
    from PIL import Image
except ImportError:
    pass
from builder.simple_button import SimpleButton, get_image

try:
    basestring
except NameError:
    basestring = str  # py3

Menuitem = namedtuple('Menuitem', ['node', 'parent_id', 'insert_after'])
Css = namedtuple('Css', ['selectors', 'declarations'])
ImageBox = namedtuple('ImageBox', ['left', 'top', 'right', 'bottom'])
Option = namedtuple('Option', ['firstline', 'xul'])
OptionPanel = namedtuple('OptionPanel', ['options', 'icon', 'panel_id'])
ChromeString = namedtuple('ChromeString', ['file_name', 'data'])
ChromeFile = namedtuple('ChromeFile', ['file_name', 'path'])

string_match = re.compile(r"StringFromName\(\"([a-zA-Z0-9.-]*?)\"")


class Button(SimpleButton):
    def __init__(self, folders, buttons, settings, applications):
        self._supported_applications = set()
        self._button_files = set()
        self._button_xul = defaultdict(dict)

        super(Button, self).__init__(folders, buttons, settings, applications)

        self._button_js = defaultdict(dict)
        self._properties_strings = set()
        self._preferences = {}
        self._button_options = defaultdict(list)
        self._button_options_js = {}
        self._option_applications = set()
        self._has_javascript = False
        self._manifest = []
        self.extra_files = {}
        self.resource_files = {}
        self._pref_list = defaultdict(list)
        self._button_style = {}
        self._option_titles = set()
        self._option_icons = set()
        self._modules = defaultdict(set)
        self._button_js_setup = defaultdict(dict)
        self._button_commands = defaultdict(dict)
        self.has_options = False
        self._interfaces = {}
        self.locales_in_use = []

        loader = FileSystemLoader([
            os.path.join(self._settings.get('project_root'), 'files'),
            os.path.join(self._settings.get('button_sdk_root'), 'templates')])
        self.env = Environment(loader=loader)

        # we always want these file
        self._button_js["loader"]["_"] = ""
        self._button_js["button"]["_"] = ""

        for folder, button, files in self._info:
            for file_name in (self._window_files + self._app_files):
                js_file = file_name + ".js"
                if (file_name == "button"
                        or set(self._settings.get("file_to_application").get(file_name, [])
                                    ).intersection(self._applications)
                        or set(chain.from_iterable(self._settings.get("file_to_application").get(name, [])
                                        for name in self._settings.get("file_map").get(file_name, []))
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
            for file_name in files:
                if file_name.endswith('option.xul'):
                    if file_name.startswith('extended') and not self._settings.get("extra_options"):
                        continue
                    with open(os.path.join(folder, file_name), "r") as option:
                        self._button_options[button].append(Option(option.readline(), option.read()))
            if "option.js" in files:
                with open(os.path.join(folder, "option.js"), "r") as option:
                    self._button_options_js[button] = option.read()
            if "files" in files:
                for file_name in os.listdir(os.path.join(folder, "files")):
                    if file_name[0] != ".":
                        self.extra_files[file_name] = os.path.join(folder, "files", file_name)
                        if file_name[-3:] == ".js" or file_name[-4:] == '.jsm':
                            with open(os.path.join(folder, "files", file_name), "r") as js_fp:
                                self._properties_strings.update(string_match.findall(js_fp.read()))
            if "res" in files:
                for file_name in os.listdir(os.path.join(folder, "res")):
                    if file_name[0] != ".":
                        self.resource_files[file_name] = os.path.join(folder, "res", file_name)
            for file_name, obj in (
                    ('res_list', self.resource_files), ('file_list', self.extra_files)):
                if file_name in files:
                    with open(os.path.join(folder, file_name), "r") as res_list:
                        for file_name in (file_name.strip()
                                for file_name in res_list if file_name.strip()):
                            obj[file_name] = self.find_file(file_name)
            if "style.css" in files:
                with open(os.path.join(folder, "style.css"), "r") as style:
                    self._button_style[button] = style.read()
            if "modules" in files:
                with open(os.path.join(folder, "modules"), "r") as modules:
                    self._modules[button].update(line.strip() for line in modules)

    def get_supported_applications(self):
        return self._supported_applications

    def get_description(self, button):
        folder = self._button_folders[button]
        with open(os.path.join(folder, "description"), "r") as description:
            return description.read()

    def _process_xul_file(self, folder, button, xul_file, file_name):
        application = SimpleButton._process_xul_file(self, folder, button, xul_file, file_name)
        if xul_file != "%s.xul" % file_name and self._button_xul.get(file_name, {}).get(button):
            return
        self._supported_applications.update(set(application).intersection(self._applications))
        self._button_files.add(file_name)
        with open(os.path.join(folder, xul_file)) as xul:
            self._button_xul[file_name][button] = xul.read().strip()

    def get_manifest(self):
        return "\n".join(self._manifest)

    def append_option(self, files, apps, first, data):
        meta = first.strip().split(':')
        if len(meta) == 2:
            title, icon = meta
        else:
            title, icon, appslist = meta
            apps = apps.intersection(appslist.split())
        self._option_icons.add(icon)
        self._option_titles.add(title)
        for app in apps:
            self._option_applications.add(app)
            if title in files[app]:
                files[app][title].options.append(data)
            else:
                files[app][title] = OptionPanel(
                    options=[data], icon=icon,
                    panel_id=title.replace('.', '-'))

    def create_menu_options(self):
        if self._settings.get("menuitems") and self._settings.get(
                "menuitems_options"):
            with open(self.find_file("show-menu-option.xul"),
                      "r") as menu_option_file:
                menu_option_template = menu_option_file.read()
            if self._settings.get(
                    "menu_placement") is None and self._settings.get(
                    "menu_meta"):
                menu_id, menu_label, location = self._settings.get("menu_meta")
                xul = self.format_string(menu_option_template,
                                         menu_id=menu_id, menu_label=menu_label)
                # TODO: add filter for the application where the menu would be
                self._button_options[menu_id].append(
                    Option("tb-show-a-menu.option.title:menu.png", xul))
                self._button_applications[menu_id] = self._applications
            else:
                menu_placement = self._settings.get("menu_placement")
                for button in self._buttons:
                    if button in self._settings.get("menuitems") or (type(
                            menu_placement) == dict and button in menu_placement):
                        xul = self.format_string(menu_option_template,
                                                 menu_id=button + "-menu-item",
                                                 menu_label=button + ".label")
                        self._button_options[button + "-menu-item"].append(
                            Option("tb-show-a-menu.option.title:menu.png", xul))
                        self._button_applications[
                            "%s-menu-item" % button] = self._applications

    def option_data(self):
        javascript = []
        if self._button_options_js:
            javascript = ["loader.js", "button.js", "option.js"]
        self.create_menu_options()
        files = defaultdict(dict)
        for button, options in self._button_options.items():
            for first, data in options:
                self.append_option(files, self._button_applications[button],
                                   first, self.string_subs(data))
        if self._pref_list:
            limit = [name + '.xul' for name in self._pref_list.keys()]
            pref_files = get_pref_folders(limit, self._settings)
            for file_name, name in zip(*pref_files):
                with open(file_name, "r") as data_fp:
                    option = Option(data_fp.readline(), data_fp.read())
                applications = set()
                for button in self._pref_list[name[:-4]]:
                    applications.update(self._button_applications[button])
                    self._button_options[file_name].append(option)
                self.append_option(files, applications, option.firstline,
                                   self.string_subs(option.xul))
        return files, javascript

    def get_options(self):
        files, javascript = self.option_data()
        template = self.env.get_template('option.xul')
        result = {}
        for application, panels in files.items():
            result[application + "-options"] = template.render(
                panels=panels.items(), javascript=javascript,
                chrome_name=self._settings.get("chrome_name"),
                locale_file_prefix=self._settings.get("locale_file_prefix")
            )
        self.has_options = bool(result)
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

    def get_files(self):
        """Iterator over a tuple of filename and data"""
        raise NotImplementedError()

    def locale_file_filter(self, strings, locales_inuse):
        default_locale = self._settings.get("default_locale")
        if strings[default_locale]:
            for locale, data in strings.items():
                if locale in locales_inuse:
                    yield locale, data

    def locale_files(self, button_locales, locales_inuse):
        """
        For option locales to be included, the get_options() method has to be called first
        """
        self.locales_in_use = locales_inuse
        for locale, files in button_locales.files:
            for file_name in files:
                with codecs.open(file_name, encoding='utf-8') as fp:
                    yield locale, file_name, fp.read()
        extra_strings = button_locales.get_string_data(self.get_extra_locale_strings(), self)
        for locale, data in self.locale_file_filter(extra_strings, locales_inuse):
            yield locale, "files.dtd", data
        properties_data = button_locales.get_properties_data(self.get_properties_strings(), self)
        for locale, data in self.locale_file_filter(properties_data, locales_inuse):
            yield locale, "button.properties", data
        if self.has_options:
            options_strings = button_locales.get_string_data(self.get_options_strings(), self)
            for locale, data in self.locale_file_filter(options_strings, locales_inuse):
                yield locale, "options.dtd", data

    def get_file_names(self):
        return self._button_files

    def get_locale_strings(self):
        locale_match = re.compile("&([a-zA-Z0-9.-]*);")
        strings = set()
        for buttons in self._button_xul.values():
            for button in buttons.values():
                strings.update(locale_match.findall(button))
        strings = list(strings)
        strings.sort()
        return strings

    def get_key_strings(self):
        strings = []
        pref_root = self._settings.get('pref_root')
        for button in self._button_keys.keys():
            strings.extend(["%skey.%s" % (pref_root, button), "%smodifier.%s" % (pref_root, button)])
        strings.sort()
        return strings

    def get_extra_locale_strings(self):
        locale_match = re.compile("&([a-zA-Z0-9.-]*);")
        strings = []
        for file_name in self.extra_files.values():
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
        for options in self._button_options.values():
            for option in options:
                strings.extend(locale_match.findall(option.xul))
        return list(set(strings))

    def pref_locale_file(self, string):
        return string.format(chrome_name=self._settings.get("chrome_name"),
                       prefex=self._settings.get("locale_file_prefix"))

    def get_pref_list(self):
        settings = []
        pref_root = self._settings.get("pref_root")
        if self._settings.get("translate_description"):
            settings.append(("extensions.{}.description".format(self._settings.get("extension_id")),
                         self.pref_locale_file("'chrome://{chrome_name}/locale/{prefex}button.properties'")))
        if self._settings.get("show_updated_prompt") or self._settings.get("add_to_main_toolbar"):
            settings.append((pref_root + self._settings.get("current_version_pref"), "''"))
        if self._settings.get("menuitems"):
            if self._settings.get("menu_placement") is None and self._settings.get("menu_meta"):
                menu_id, menu_label, location = self._settings.get("menu_meta")
                settings.append(("{}showamenu.{}".format(pref_root, menu_id), self._settings.get("default_show_menu_pref")))
            else:
                for button in self._buttons:
                    settings.append(("{}showamenu.{}-menu-item".format(pref_root, button), self._settings.get("default_show_menu_pref")))
        for name, value in self._preferences.items():
            settings.append((pref_root + name, value))
        return settings

    def get_defaults(self):
        return "\n".join("pref('{}', {});".format(name, value)
                         for name, value in self.get_pref_list())

    def get_chrome_strings(self):
        for name, path in self.extra_files.items():
            with codecs.open(path, encoding='utf-8') as fp:
                ChromeString(file_name=os.path.join("chrome", "content", "files", name),
                         data=self.string_subs(fp.read()))
        yield ChromeString(file_name="install.rdf", data=self.create_install())
        yield ChromeString(file_name="chrome.manifest", data='\n'.join(self.manifest_lines()))

    def get_chrome_files(self):
        for name, path in self.resource_files.items():
            yield ChromeFile(file_name=os.path.join("chrome", "content", "resources", name), path=path)
        yield ChromeFile(file_name="LICENSE", path=self.find_file(self._settings.get("license", "LICENSE")))

    def create_install(self):
        template = self.env.get_template('install.rdf')
        applications = chain.from_iterable(self._settings.get("applications_data").get(application)
                        for application in self.get_supported_applications())
        return template.render(
            ext_options=self.get_options_applications(),
            ext_applications=applications,
            **self._settings)

    def manifest_lines(self):
        lines = []
        chrome_name=self._settings.get("chrome_name")
        lines.append("content\t{chrome}\tchrome/content/".format(chrome=chrome_name))
        lines.append("skin\t{chrome}\tclassic/1.0\tchrome/skin/".format(chrome=chrome_name))
        for option in self.get_options_applications():
            for _, application_id, _, _ in self._settings.get("applications_data")[option]:
                lines.append("override\tchrome://{chrome}/content/options.xul\t"
                             "chrome://{chrome}/content/{application}"
                             "-options.xul\tapplication={app_id}".format(chrome=chrome_name, app_id=application_id, application=option))
        manifest = self.get_manifest()
        if manifest:
            lines.append(manifest.format(chrome=chrome_name))
        for locale in self.locales_in_use:
            lines.append("locale\t{chrome}\t{locale}"
                         "\tchrome/locale/{locale}/".format(chrome=chrome_name, locale=locale))
        return lines
    
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
        if self._settings.get('menuitems') or (self._settings.get("icon") and self._settings.get("menu_meta")):
            icon_size["menu"] = "16"
        return icon_size

    @staticmethod
    def _get_selectors(button, group_menu_name, icon_size_set, icon_sizes, modifier):
        selectors = dict((key, list()) for key in icon_size_set)
        if modifier and (modifier[0] == ' ' or modifier[0] == '$'):
            sizes = {'menuitem': '16'}
        else:
            sizes = icon_sizes
        for name, size in sizes.items():
            if size is None:
                continue
            if name == "small":
                selectors[size].append("toolbar[iconsize='small'] toolbarbutton#{}{}".format(button, modifier))
            elif name == "large":
                selectors[size].append("toolbar toolbarbutton#{}{}".format(button, modifier))
            elif name == "menu":
                if button == group_menu_name:
                    selectors[size].append("menu#{}".format(button))
                    selectors[size].append("menuitem#{}".format(button))
                else:
                    selectors[size].append("menu#{}-menu-item{}".format(button, modifier))
                    selectors[size].append("menuitem#{}-menu-item{}".format(button, modifier))
            elif name == "window" or name == 'menuitem':
                if modifier and modifier[0] == '$':
                    selectors[size].append(modifier[1:])
                else:
                    selectors[size].append("#{}{}".format(button, modifier))
                    selectors[size].append("#{}-menu-item{}".format(button, modifier))
        return selectors

    @staticmethod
    def _box_cmp(x, offset, size):
        y_offset = offset // x
        x_offset = offset % x
        return ImageBox(x_offset * int(size), y_offset * int(size), (x_offset + 1) * int(size), (y_offset + 1) * int(size))

    def _css_setup(self):
        icon_sizes = self.get_icon_size()
        icon_size_set = {size for size in icon_sizes.values() if size is not None}
        icon_size_set.add("16")  # needed for some selectors that assume this size
        group_menu_name = self._settings.get("menu_meta")[0] if self._settings.get("menu_meta") else None
        if self._settings.get("icon") and self._settings.get('menu_placement') is None and group_menu_name:
            self._button_image[group_menu_name] = [(self._settings.get("icon"), ' ')]
        return group_menu_name, icon_size_set, icon_sizes

    def _get_css(self):
        result_images = defaultdict(set)
        image_datas = {}
        css_data = []
        chrome_name = self._settings.get("chrome_name")
        group_menu_name, icon_size_set, icon_sizes = self._css_setup()
        for button, image_data in self._button_image.items():
            for image, modifier in image_data:
                original_image = image
                if image[0] == "*" or image[0] == "-":
                    data, image = self.create_grayscale(icon_size_set, image)
                    if data is None:
                        continue
                    for size in icon_size_set:
                        image_datas[os.path.join("skin", size, image)] = data[size]
                selectors = self._get_selectors(button, group_menu_name, icon_size_set, icon_sizes, modifier)
                for size in (size for size in icon_size_set if len(selectors[size])):
                    if original_image[0] != "*" and original_image[0] != "-":
                        result_images[size].add(image)
                    declarations = [
                        """list-style-image:url("chrome://{chrome_name}/skin/{size}/{image}");""".format(chrome_name=chrome_name, size=size, image=image),
                        """-moz-image-region: rect(0px {size}px {size}px 0px);""".format(size=size)
                    ]
                    css_data.append(Css(
                        selectors=",\n".join(selectors[size]),
                        declarations=declarations))
        return icon_sizes, image_datas, css_data, result_images

    def create_grayscale(self, icon_size_set, image):
        new_image = image[1:].replace('.', '-disabled.', 1)
        opacity = 1.0 if image[0] == "-" else 0.9
        data = {}
        try:
            for size in icon_size_set:
                data[size] = grayscale.image_to_graysacle(
                        get_image(self._settings, size, image[1:]), opacity)
            return data, new_image
        except ValueError:
            print("image %s does not exist" % image)
        return None, None

    def _get_css_merge(self):
        result_images = defaultdict(set)
        image_datas = {}
        group_menu_name, icon_size_set, icon_sizes = self._css_setup()
        image_map = {}
        image_set = set()
        css_data = []
        chrome_name = self._settings.get("chrome_name")
        for button, image_data in self._button_image.items():
            for image, modifier in image_data:
                image_set.add(image)
        image_count = len(image_set)
        image_map_size = {}
        image_map_x = {}
        for size in icon_size_set:
            y, x = int(math.ceil(image_count * int(size) / 1000.0)), (1000 // int(size))
            if y == 1:
                x = image_count
            image_map_x[size] = x
            image_map_size[size] = Image.new("RGBA", (x * int(size), y * int(size)), (0, 0, 0, 0))
        count = 0

        def merge_image(count, func, image):
            image_map[image] = count
            for size in icon_size_set:
                # TODO: need to also check if this icon will never be needed
                # if modifier and (modifier[0] == ' ' or modifier[0] == '$') and size != '16':
                # continue
                image_map_size[size].paste(
                    func(image, size),
                    self._box_cmp(image_map_x[size], count, size))

        for button, image_data in self._button_image.items():
            for image, modifier in image_data:
                index = image_map.get(image)
                if index is not None:
                    offset = index
                else:
                    if image[0] == "*" or image[0] == "-":
                        data, image = self.create_grayscale(icon_size_set, image)
                        if data is None:
                            continue

                        def gray_image(image, size):
                            return Image.open(io.BytesIO(data[size]))
                        merge_image(count, gray_image, image)
                    else:
                        def create_image(image, size):
                            try:
                                return Image.open(get_image(self._settings, size, image))
                            except IOError:
                                print("image %s does not exist" % image)
                        merge_image(count, create_image, image)
                    count, offset = count + 1, count
                selectors = self._get_selectors(button, group_menu_name, icon_size_set, icon_sizes, modifier)
                for size in (size for size in icon_size_set if len(selectors[size])):
                    image_box = self._box_cmp(image_map_x[size], offset, size)
                    declarations = [
                        """list-style-image:url("chrome://{chrome_name}/skin/{size}/button.png");""".format(chrome_name=chrome_name, size=size),
                        """-moz-image-region: rect({top}px {right}px {bottom}px {left}px)""".format(**image_box._asdict())
                    ]
                    css_data.append(Css(
                        selectors=",\n".join(selectors[size]),
                        declarations=declarations))
        for size in icon_size_set:
            size_io = io.BytesIO()
            image_map_size[size].save(size_io, "png")
            image_datas[os.path.join("skin", size, "button.png")] = size_io.getvalue()
            size_io.close()
        return icon_sizes, image_datas, css_data, result_images

    def get_css_file(self):
        template = self.env.get_template("button.css")
        if self._settings.get("merge_images"):
            icon_sizes, image_datas, css_data, result_images = self._get_css_merge()
        else:
            icon_sizes, image_datas, css_data, result_images = self._get_css()
        chrome_name = self._settings.get("chrome_name")
        if self._settings.get("include_toolbars"):
            for name, selector in (('small', "toolbar[iconsize='small'] .toolbar-buttons-toolbar-toggle"),
                                   ('large', 'toolbar .toolbar-buttons-toolbar-toggle'), 
                                   ('window', '.toolbar-buttons-toolbar-toggle')):
                if icon_sizes[name] is not None:
                    result_images[icon_sizes[name]].add(self._settings.get("icon"))
                    css_data.append(Css(
                        selectors=selector,
                        declarations="""list-style-image:url("chrome://{chrome_name}/skin/{size}/{icon}");))""".format(icon=self._settings.get("icon"), size=icon_sizes[name], chrome_name=chrome_name)))
        css = template.render(
            blocks=set(self._button_style.values()),
            css_data=css_data
        )
        return css, result_images, image_datas

    def get_js_files(self):
        interface_match = re.compile(r"(?<=toolbar_buttons.interfaces.)[a-zA-Z]*")
        function_match = re.compile(r"^[a-zA-Z0-9_]*\s*:\s*(?:function\([^\)]*\)\s*)?\{.*?^\}[^\n]*",
                                    re.MULTILINE | re.DOTALL)
        function_name_match = re.compile(r"((^[a-zA-Z0-9_]*)\s*:\s*(?:function\s*\([^\)]*\)\s*)?\{.*?^\})",
                                          re.MULTILINE | re.DOTALL)
        detect_dependency = re.compile(r"(?<=toolbar_buttons.)[a-zA-Z]*")

        multi_line_replace = re.compile(r"\n{2,}")
        js_files = defaultdict(str)
        js_includes = set()
        js_options_include = set()
        js_imports = set()
        
        # we look though the XUL for functions first
        for file_name, values in self._button_xul.items():
            for button, xul in values.items():
                js_imports.update(detect_dependency.findall(xul))
        if self._settings.get("menuitems"):
            js_imports.add("sortMenu")
            js_imports.add("handelMenuLoaders")
            js_imports.add("setUpMenuShower")
        if self._settings.get("use_keyboard_shortcuts"):
            js_imports.add("settingWatcher")

        for file_name, js in self._button_js.items():
            js_file = "\n".join(js.values())
            js_functions = function_match.findall(js_file)
            js_imports.update(detect_dependency.findall(js_file))
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
        externals = {}
        lib_folders = [os.path.join(self._settings.get("button_sdk_root"), "files", "lib"),
                       os.path.join(self._settings.get("project_root"), "files", "lib")]
        for lib_folder in lib_folders:
            if os.path.isdir(lib_folder):
                for file_name in os.listdir(lib_folder):
                    with open(os.path.join(lib_folder, file_name), "r") as shared_functions_file:
                        externals.update({name: function for function, name
                                 in function_name_match.findall(shared_functions_file.read())})
        if self._settings.get("include_toolbars"):
            js_imports.add("toggleToolbar")
        extra_functions = []
        js_imports.update(js_includes)
        loop_imports = js_imports
        while loop_imports:
            new_extra = [externals[func_name] for func_name in loop_imports
                    if func_name in js_imports if func_name in externals]
            extra_functions.extend(new_extra)
            new_imports = set(detect_dependency.findall("\n".join(new_extra)))
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
            for options in self._button_options.values():
                for option in options:
                    js_options_include.update(detect_dependency.findall(option.xul))
            for button, value in self._button_options_js.items():
                # TODO: dependency resolution is not enabled here yet
                js_options_include.update(detect_dependency.findall(value))
                js_functions = function_match.findall(value)
                self._button_options_js[button] = ",\n".join(js_functions)
                extra_javascript.append(multi_line_replace.sub("\n",
                                        function_match.sub("", value).strip()))
            self._button_options_js.update(dict((name, function) for name, function
                               in externals.items() if name in js_options_include))
            with open(os.path.join(self._settings.get('button_sdk_root'), "templates", "option.js")) as option_fp:
                js_files["option"] = (option_fp.read()
                    % ("\n\t".join(",\n".join(val for val in self._button_options_js.values() if val).split("\n")), "\n".join(extra_javascript)))
        interfaces_file = os.path.join(self._settings.get('project_root'), 'files', 'interfaces')
        if not os.path.isfile(interfaces_file):
            interfaces_file = os.path.join(self._settings.get('button_sdk_root'), 'templates', 'interfaces')
        interfaces = {}
        with open(interfaces_file, "r") as interfaces_data:
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

    @staticmethod
    def _list_has_str(lst, text):
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
        if self._has_javascript and file_name in self._button_js and file_name not in js_files:
            js_files.append(file_name)
        return js_files
