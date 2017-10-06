"""Takes some settings in the build_extension and creates a Toolbar Buttons
   extension from it"""

import os
import zipfile
from builder.locales import Locale
from builder.button import RestartlessButton, OverlayButton, WebExtensionButton, SimpleButton, ExtensionConfigError
from builder.util import get_locale_folders, get_folders
from builder.app_versions import get_app_versions

try:
    basestring
except NameError:
    basestring = str  # py3
    unicode = str

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
    button_list = set()
    buttons = settings.get("buttons", ())
    if isinstance(buttons, basestring):
        buttons = buttons.split(",")
    if buttons:
        button_list.update(buttons)
    menuitems = settings.get("menuitems", ())
    if isinstance(menuitems, basestring):
        menuitems = menuitems.split(",")
    if menuitems and not settings.get('webextension'):
        button_list.update(menuitems)
    button_folders, button_names = [], []
    for name in settings.get("projects"):
        staging_button_folders, staging_buttons = get_folders(button_list, settings, name)
        button_folders.extend(staging_button_folders)
        button_names.extend(staging_buttons)
    if not cls:
        if settings.get('restartless'):
            cls = RestartlessButton
        elif settings.get('webextension'):
            cls = WebExtensionButton
        else:
            cls = OverlayButton
    menuitems = settings.get("menuitems")
    menu_placement = settings.get("menu_placement")
    if(type(menu_placement) == dict):
        settings["menuitems"] = menu_placement.keys()
    elif not menuitems:
        settings["menuitems"] = ()
    elif "all" in menuitems:
        if 'menuitems_sorted' not in settings:
            settings["menuitems_sorted"] = True
        settings["menuitems"] = button_names
    buttons = cls(button_folders, button_names, settings, applications)
    return buttons


def create_objects(settings, button_locales=None):
    if settings.get("image_path") is None:
        raise ExtensionConfigError("Please set the image_path setting")
    if button_locales is None:
        locale_folders, locales = get_locale_folders(settings.get("locale"),
                                                     settings)
        button_locales = Locale(settings, locale_folders, locales)
    else:
        button_locales = Locale.from_locale(settings, button_locales)
        locales = button_locales.locales
    buttons = get_buttons(settings)
    if len(buttons.buttons()) == 0:
        raise ExtensionConfigError("The selected config would have no buttons.")
    return button_locales, buttons, locales

def build_webextension(settings):
    buttons = get_buttons(settings, SimpleButton)
    manifests = buttons.manifests()
    for button in manifests:
        config = dict(settings)
        config['buttons'] = [button]
        config['output_file'] = "{}-button-{}.xpi".format(button, settings.get('version'))
        config['output_locales_file'] = "{}-button.zip".format(button)
        if 'extension_id' in manifests.get(button):
            config['extension_id'] = manifests.get(button).get('extension_id')
        else:
            config['extension_id'] = "{}-single@codefisher.org".format(button)
        build_extension(config)

def build_individual(settings):
    buttons = get_buttons(settings, SimpleButton)
    for button in buttons.buttons():
        config = dict(settings)
        config['buttons'] = [button]
        config['output_file'] = "{}-button-{}.xpi".format(button, settings.get('version'))
        config['output_locales_file'] = "{}-button.zip".format(button)
        config['extension_id'] = "{}-individual@codefisher.org".format(button)
        build_extension(config)

def build_extension(settings, output=None, project_root=None, button_locales=None):
    button_locales, buttons, locales = create_objects(settings, button_locales)
    xpi_file_name = os.path.join(
        settings.get("project_root"),
        settings.get("output_folder"),
        settings.get("output_file", "toolbar_buttons.xpi") % settings)
    if output:
        xpi = zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED)
    else:
        xpi = zipfile.ZipFile(xpi_file_name, "w", zipfile.ZIP_DEFLATED)
    
    if settings.get("fix_meta"):
        locale_name = locales[0] if len(locales) == 1 else None
        locale_str = buttons.locale_string(
            button_locale=button_locales, locale_name=locale_name)
        def label_get(button):
            title_string = buttons.manifests().get(button, {}).get('name')
            if title_string:
                name = button_locales.get_dtd_value(locale_name, title_string, button)
                if name:
                    return name
                return buttons.get_string(title_string, locale_name)
            return locale_str("label", button)
        labels = sorted((label_get(button)
                         for button in buttons.buttons()), key=unicode.lower)
        if len(buttons) == 1:
            button = buttons.buttons()[0]
            settings["name"] = labels[0] + " Button"
            settings["description"] = buttons.get_description(button)
            if not settings.get("icon"):
                settings["icon"] = buttons.get_icons(button)
        else:
            description = u"A customized version of {} including the buttons: {}"
            settings["description"] = description.format(
                settings["name"], u", ".join(labels))

    if not output:
        zip_file_name = os.path.join(
            settings.get("project_root"),
            settings.get("output_folder"),
            settings.get("output_locales_file", "locales.zip") % settings)
        zip = zipfile.ZipFile(zip_file_name, "w", zipfile.ZIP_DEFLATED)
        for locale, name, data in buttons.locale_files(button_locales):
            zip.writestr("{}/{}".format(locale, name), data)
        zip.close()

    for name, data in buttons.get_file_strings(settings, button_locales):
        xpi.writestr(name, data)

    for name, file in buttons.get_files_names(settings):
        xpi.write(name, file)

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