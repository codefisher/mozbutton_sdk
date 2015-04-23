import os
import json
import codecs
import itertools

try:
    basestring # problem in Py3
except NameError:
    basestring = str

try:
    import svn.local
except ImportError:
    pass

try:
    from git import Repo
except ImportError:
    pass

def apply_settings_files(settings, file_names):
    for file_name in file_names:
        if not settings.get("project_root"):
            settings["project_root"] = os.path.abspath(os.path.join(os.path.dirname(file_name)))
        try:
            with codecs.open(file_name, encoding='utf-8') as fp:
                try:
                    settings.update(json.load(fp))
                except ValueError:
                    raise ValueError("Failed to parse settings file: %s" % file_name)
        except IOError:
            raise IOError("Failed to open settings file: %s" % file_name)

def get_svn_revision(settings):
    repo = svn.local.LocalClient(settings.get("project_root"))
    return repo.info().get("commit#revision")

def get_git_revision(settings):
    repo = Repo(settings.get("project_root"))
    return repo.head.commit.count()

def get_button_folders(limit, settings, data_folder="data"):
    return get_folders(limit, settings, data_folder)

def get_locale_folders(limit, settings, data_folder="locale"):
    return get_folders(limit, settings, data_folder)

def get_pref_folders(limit, settings, data_folder="options"):
    return get_folders(limit, settings, data_folder)

def get_folders(limit, settings, folder):
    """Gets all the folders inside another and applies some filtering to it

    filter maybe the value "all" or a comer seperated list of values

    get_folders(str, str) -> list<str>
    """
    if settings.get("project_root"):
        folder = os.path.join(settings.get("project_root"), folder)
    folders = [file_name for file_name in os.listdir(folder)
               if not file_name.startswith(".")]
    if isinstance(limit, basestring):
        limit = limit.split(",")
    if "all" not in limit:
        folders = list(set(folders).intersection(set(limit)))
    else:
        limits = [item[1:] for item in limit if item[0] == "-"]
        folders = list(folder for folder in folders if folder not in limits)
    return [os.path.join(folder, sub_folder) for sub_folder in folders], folders

def extra_update_prams():
    app_data = {
        "item_id": "%ITEM_ID%",
        "item_version": "%ITEM_VERSION%",
        "item_maxapversion": "%ITEM_MAXAPPVERSION%",
        "app_version": "%APP_VERSION%",
        "req_version": "%REQ_VERSION%",
        "item_status": "%ITEM_STATUS%",
        "app_id": "%APP_ID%",
        "current_app_version": "%CURRENT_APP_VERSION%",
        "app_os": "%APP_OS%",
        "app_abi": "%APP_ABI%",
        "app_locale": "%APP_LOCALE%",
        "update_type": "%UPDATE_TYPE%",
        "compatibility_mode": "%COMPATIBILITY_MODE%",
    }
    return "&".join("%s=%s" % (key, value) for key, value in app_data.items())

def create_update_rdf(config):
    xml = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:em="http://www.mozilla.org/2004/em-rdf#">
    <rdf:Description
        rdf:about="urn:mozilla:extension:%s">
        <em:updates>
            <rdf:Seq>
                <rdf:li>
                    <rdf:Description>
                        <em:version>%s</em:version>
                        %s
                    </rdf:Description>
                </rdf:li>
            </rdf:Seq>
        </em:updates>
    </rdf:Description>
    </rdf:RDF>"""
    
    update_xml = """<!--  %%s -->
                        <em:targetApplication>
                            <rdf:Description>
                                <em:id>%%s</em:id>
                                <em:minVersion>%%s</em:minVersion>
                                <em:maxVersion>%%s</em:maxVersion>
                                <em:updateLink>%s</em:updateLink>
                            </rdf:Description>
                        </em:targetApplication>""" % config.get("update_file")
                        
    updates = []
    for data in itertools.chain(*config.get("applications_data").values()):
        updates.append(update_xml % tuple(data))
    return xml % (config.get("extension_id"), config.get("version"), "\n".join(updates))