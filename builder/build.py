"""Takes some settings in the build_extension and creates a Toolbar Buttons
   extension from it"""

import os
import zipfile
from builder.locales import Locale
from builder.button import get_image, RestartlessButton, OverlayButton, Button
from builder.util import get_locale_folders, get_folders
from builder.app_versions import get_app_versions

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
            settings["name"] = labels[0] + " Button"
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

    locale_prefix = settings.get("locale_file_prefix")
    for locale, file_name, data in buttons.locale_files(button_locales):
        xpi.writestr(os.path.join("chrome", "locale", locale,
                locale_prefix + file_name), bytes_string(data))

    for chrome_string in buttons.get_chrome_strings():
        xpi.writestr(chrome_string.file_name, bytes_string(chrome_string.data))
    for chrome_file in buttons.get_chrome_files():
        xpi.write(chrome_file.path, chrome_file.file_name)
    
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
        path = get_image(settings, "32", settings.get("icon"))
        xpi.write(path, "icon.png")
        xpi.write(path, os.path.join("chrome", "skin", "icon.png"))
    else:
        path = os.path.join(settings.get("project_root"), "files", "icon.png")
        xpi.write(path, "icon.png")
        xpi.write(path, os.path.join("chrome", "skin", "icon.png"))

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