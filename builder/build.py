"""Takes some settings in the build_extension and creates a Toolbar Buttons
   extension from it"""

import os
import zipfile
from builder.locales import Locale
from builder.button import get_image, RestartlessButton, OverlayButton, Button
from builder.util import get_locale_folders, get_folders
from builder.app_versions import get_app_versions
import codecs
from collections import defaultdict

class ExtensionConfigError(Exception):
    pass

def bytes_string(string):
    try:
        if type(string) == unicode:
            return str(string.encode("utf-8"))
        return string
    except:
        return string.encode("utf-8")

def apply_max_version(settings):
    versions = get_app_versions()
    app_data = settings.get("applications_data")
    for key, app_set in app_data.items():
        rows = []
        for item in app_set:
            item = list(item)
            item[3] = versions.get(item[1], item[3])
            rows.append(item)
        app_data[key] = rows


def get_buttons(settings, cls=None):
    if "all" in settings.get("applications", "all"):
        applications = settings.get("applications_data").keys()
    elif isinstance(settings.get("applications"), basestring):
        if "," in settings.get("applications"):
            applications = settings.get("applications").split(',')
        else:
            applications = settings.get("applications").split('-')
    else:
        applications = settings.get("applications")
    button_list = settings.get("buttons")
    button_folders, button_names = [], []
    for name in settings.get("projects"):
        staging_button_folders, staging_buttons = get_folders(button_list, settings, name)
        button_folders.extend(staging_button_folders)
        button_names.extend(staging_buttons)
    if not cls:
        if settings.get('restartless'):
            cls = RestartlessButton
        else:
            cls = OverlayButton
    menuitems = settings.get("menuitems")
    menu_placement = settings.get("menu_placement")
    if(type(menu_placement) == dict):
        settings["menuitems"] = menu_placement.keys()
    elif not menuitems:
        settings["menuitems"] = ()
    elif "all" in menuitems:
        settings["menuitems"] = button_names
    buttons = cls(button_folders, button_names, settings, applications)
    return buttons

def build_extension(settings, output=None, project_root=None, button_locales=None):
    if os.path.join(settings.get("image_path")) is None:
        print("Please set the image_path setting")
        return
    if button_locales is None:
        locale_folders, locales = get_locale_folders(settings.get("locale"), settings)
        button_locales = Locale(settings, locale_folders, locales)
    else:
        button_locales = Locale.from_locale(settings, button_locales)
        locales = button_locales.locales
    buttons = get_buttons(settings)
    if len(buttons.buttons()) == 0:
        raise ExtensionConfigError("The selected config would have no buttons.")
    
    xpi_file_name = os.path.join(settings.get("project_root"), settings.get("output_folder"), settings.get("output_file", "toolbar_buttons.xpi") % settings)
    if output:
        xpi = zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED)
    else:
        xpi = zipfile.ZipFile(xpi_file_name, "w", zipfile.ZIP_DEFLATED)
    
    for file, data in buttons.get_js_files().items():
        xpi.writestr(os.path.join("chrome", "content", file + ".js"),
                data.replace("{{uuid}}", settings.get("extension_id")))
    
    for file_name, data in buttons.get_files():
        xpi.writestr(os.path.join("chrome", "content", file_name), bytes_string(data))

    if settings.get("fix_meta"):
        locale_str = buttons.locale_string(button_locale=button_locales, locale_name=locales[0] if len(locales) == 1 else None)
        labels = sorted([locale_str("label", button) for button in buttons.buttons()], key=unicode.lower)
        if len(buttons) == 1:
            button = buttons.buttons()[0]
            settings["name"] = "%s Button" % labels[0]
            settings["description"] = buttons.get_description(button)
            if not settings.get("icon"):
                settings["icon"] = buttons.get_icons(button)
        else:
            settings["description"] = "A customized version of Toolbar Buttons including the buttons: %s" % ", ".join(labels)

    options = buttons.get_options()
    for file, data in options.items():
        xpi.writestr(os.path.join("chrome", "content", "%s.xul" % file), data)
    for image in buttons.get_option_icons():
        xpi.write(get_image(settings, "32", image), os.path.join("chrome", "skin", "option", image))
    option_applicaions = buttons.get_options_applications()

    locale_prefix = settings.get("locale_file_prefix")
    locales_inuse = set()
    for locale, file_name, data in buttons.locale_files(button_locales):
        xpi.writestr(os.path.join("chrome", "locale", locale,
                locale_prefix + file_name), bytes_string(data))
        locales_inuse.add(locale)

    for name, path in buttons.extra_files.items():
        with codecs.open(path, encoding='utf-8') as fp:
            xpi.writestr(os.path.join("chrome", "content", "files", name), 
                         bytes_string(fp.read().replace("{{chrome_name}}", settings.get("chrome_name"))
                            .replace("{{pref_root}}", settings.get("pref_root"))
                            .replace("{{locale_file_prefix}}", settings.get("locale_file_prefix"))))
    has_resources = bool(buttons.resource_files)
    for name, path in buttons.resource_files.items():
        xpi.write(path, os.path.join("chrome", "content", "resources", name))
    
    css, result_images, image_data = buttons.get_css_file()
    xpi.writestr(os.path.join("chrome", "skin", "button.css"), bytes_string(css))
    for size, image_list in result_images.items():
        for image in set(image_list):
            if size is not None:
                try:
                    xpi.write(get_image(settings, size, image), os.path.join("chrome", "skin", size, image))
                except (OSError, IOError):
                    xpi.write(get_image(settings, size, "picture-empty.png"), os.path.join("chrome", "skin", size, image))
                    print("can not find file %s" % image)
    for file_name, data in image_data.items():
        xpi.writestr(os.path.join("chrome", file_name), data)
    if settings.get("icon"):
        xpi.write(get_image(settings, "32", settings.get("icon")), "icon.png")
        xpi.write(get_image(settings, "32", settings.get("icon")), os.path.join("chrome", "skin", "icon.png"))
    else:
        xpi.write(os.path.join(settings.get("project_root"), "files", "icon.png"), "icon.png")
        xpi.write(os.path.join(settings.get("project_root"), "files", "icon.png"), os.path.join("chrome", "skin", "icon.png"))
    xpi.writestr("chrome.manifest", create_manifest(settings, locales_inuse, buttons, has_resources, option_applicaions))
    xpi.writestr("install.rdf", create_install(settings, buttons.get_supported_applications(), option_applicaions))
    if settings.get('restartless'):
        xpi.writestr("bootstrap.js", create_bootstrap(settings, buttons, has_resources))
        xpi.write(os.path.join(settings.get('button_sdk_root'), "templates", "customizable.jsm"), 
                  os.path.join("chrome", "content", "customizable.jsm"))
    licence_file = os.path.join(settings.get("project_root"), "files", settings.get("license", "LICENSE"))
    if os.path.isfile(licence_file):
        xpi.write(licence_file, "LICENSE")
    else:
        xpi.write(os.path.join(settings.get('button_sdk_root'), "templates", "LICENSE"), "LICENSE")
    defaults =  buttons.get_defaults()
    if defaults:
        if settings.get('restartless'):
            xpi.writestr(os.path.join("chrome", "content", "defaultprefs.js"), defaults)   
        else:
            xpi.writestr(os.path.join("defaults", "preferences", "toolbar_buttons.js"), defaults)
    
    xpi.close()
    if not output and settings.get("profile_folder"):
        with open(xpi_file_name, "r") as xpi_fp:
            data = xpi_fp.read()
            for folder in settings.get("profile_folder"):
                try:
                    with open(os.path.join(folder, "extensions",
                        settings.get("extension_id") + ".xpi"), "w") as fp:
                        fp.write(data)
                except IOError:
                    print("Failed to write extension to profile folder")
    return buttons

def create_bootstrap(settings, buttons, has_resources):
    chrome_name = settings.get("chrome_name")
    loaders = []
    resource = ""
    if has_resources:
        resource = "createResource('%s', 'chrome://%s/content/resources/');" % (chrome_name, chrome_name)
    install = ""
    window_modules = defaultdict(list)
    for file_name in buttons.get_file_names():
        for overlay in settings.get("files_to_window").get(file_name, ()):
            window_modules[overlay].append(file_name)
            
    for overlay, modules in window_modules.items():
            mods = "\n\t\t".join(["modules.push('chrome://%s/content/%s.jsm');" % (chrome_name, file_name) for file_name in modules])
            loaders.append("(uri == '%s') {\n\t\t%s\n\t}" % (overlay, mods))
    with open(os.path.join(settings.get('button_sdk_root'), "templates", "bootstrap.js") ,"r") as f:
        template = f.read()
    if settings.get("show_updated_prompt"):
        with open(os.path.join(settings.get('button_sdk_root'), "templates", "install.js") ,"r") as f:
            install = (f.read().replace("{{homepage_url}}", settings.get("homepage"))
                               .replace("{{version}}", settings.get("version"))
                               .replace("{{pref_root}}", settings.get("pref_root"))
                               .replace("{{current_version_pref}}", settings.get("current_version_pref")))
    return (template.replace("{{chrome_name}}", settings.get("chrome_name"))
                    .replace("{{resource}}", resource)
                    .replace("{{install}}", install)
                    .replace("{{loaders}}", "if" + " else if".join(loaders)))

def create_manifest(settings, locales, buttons, has_resources, options=[]):
    lines = []
    values = {"chrome": settings.get("chrome_name")}

    lines.append("content\t{chrome}\tchrome/content/".format(**values))
    lines.append("skin\t{chrome}\tclassic/1.0\tchrome/skin/".format(**values))
    if not settings.get('restartless'):
        lines.append("style\tchrome://global/content/customizeToolbar.xul"
                 "\tchrome://{chrome}/skin/button.css".format(**values))

    if has_resources and not settings.get('restartless'):
        lines.append("resource\t{chrome}\tchrome://{chrome}/content/resources/".format(**values))
    for option in options:
        values["application"] = option
        for _, application_id, _, _ in settings.get("applications_data")[option]:
            values["id"] = application_id
            lines.append("override\tchrome://{chrome}/content/options.xul\t"
                         "chrome://{chrome}/content/{application}"
                         "-options.xul\tapplication={id}".format(**values))

    if not settings.get('restartless'):
        for file_name in buttons.get_file_names():
            values["file"] = file_name
            for overlay in settings.get("files_to_overlay").get(file_name, ()):
                values["overlay"] = overlay
                lines.append("overlay\t{overlay}\t"
                             "chrome://{chrome}/content/{file}.xul".format(**values))
    manifest = buttons.get_manifest()
    if manifest:
        lines.append(manifest.format(**values))

    for locale in locales:
        values["locale"] = locale
        lines.append("locale\t{chrome}\t{locale}"
                     "\tchrome/locale/{locale}/".format(**values))
    return "\n".join(lines)

def create_install(settings, applications, options=[]):
    """Creates the install.rdf file for the extension"""
    if options:
        options_url = ("\t\t<em:optionsURL>chrome://{}/content/options.xul"
                       "</em:optionsURL>\n".format(settings.get("chrome_name")))
    else:
        options_url = ""
    if settings.get("restartless"):
        bootstrap = "<em:bootstrap>true</em:bootstrap>"
    else:
        bootstrap = ""
    if settings.get("update_url"):
        update_url = bytes_string("\t\t<em:updateURL>%s</em:updateURL>\n" % settings.get("update_url"))
    else:
        update_url = ""
    supported_applications = []
    for application in applications:
        for values in settings.get("applications_data")[application]:
            supported_applications.append("""
        \t\t<!-- %s -->
        \t\t<em:targetApplication>
            \t\t\t<Description>
                \t\t\t\t<em:id>%s</em:id>
                \t\t\t\t<em:minVersion>%s</em:minVersion>
                \t\t\t\t<em:maxVersion>%s</em:maxVersion>
            \t\t\t</Description>
        \t\t</em:targetApplication>""".replace(" ","") % tuple(values))
    install_file = os.path.join(settings.get("project_root"), "files", "install.rdf")
    if not os.path.isfile(install_file):
        install_file = os.path.join(settings.get('button_sdk_root'), "templates", "install.rdf")
    with codecs.open(install_file,"r", encoding='utf-8') as f:
        template = f.read()
    return bytes_string(template.replace("{{uuid}}", settings.get("extension_id"))
                    .replace("{{name}}", settings.get("name"))
                    .replace("{{version}}", settings.get("version"))
                    .replace("{{description}}", settings.get("description"))
                    .replace("{{creator}}", settings.get("creator"))
                    .replace("{{chrome_name}}", settings.get("chrome_name"))
                    .replace("{{homepageURL}}", settings.get("homepage"))
                    .replace("{{optionsURL}}", options_url)
                    .replace("{{bootstrap}}", bootstrap)
                    .replace("{{updateUrl}}", update_url)
                    .replace("{{applications}}",
                             "".join(supported_applications))
            )
