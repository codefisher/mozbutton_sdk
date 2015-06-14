import sys
import os
import re
import json
from config import settings
import hashlib

def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)

def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        print("Please give the location of where you want to start the project.")
        exit()
    create_folder(path)
    create_folder(os.path.join(path, "buttons"))
    create_folder(os.path.join(path, "locale", "en-US"))
    create_folder(os.path.join(path, "extensions"))
    create_folder(os.path.join(path, "files", "lib"))
    create_folder(os.path.join(path, "options"))

    ext_info = {
        "version": "1.0",
        "projects": ["buttons"],
        "buttons": "all",
        "translate_description": True,
        "restartless": True,
        "default_locale": "en-US",
    }

    name = raw_input("Extension Name: ")
    simple_name = re.sub(r"[^a-zA-Z]+", '_', name).lower()
    ext_info["name"] = name
    ext_info["chrome_name"] = simple_name
    ext_info["pref_root"] = "extensions.{}.".format(simple_name)
    ext_id = raw_input("Extension ID (leave blank to have one generated): ")
    if ext_id:
        ext_info["extension_id"] = ext_id
    else:
        m = hashlib.md5()
        m.update(name)
        ext_info["extension_id"] = "{" + m.hexdigest() + "}"

    ext_info["creator"] = raw_input("Extension Creator: ")
    ext_info["description"] = raw_input("Extension Description: ")
    ext_info["homepage"] = raw_input("Extension Homepage: ")

    applications = sorted(settings.config.get("applications_data").keys() + ["all"])
    dfiles = list(enumerate(applications))

    print("Please select what application you want to support (you can add more later).\nPress enter to finish.")
    for i, name in dfiles:
        print("    [{0}] {1}".format(i, name))
    apps = []
    while True:
        try:
            selection = raw_input("Application: ").strip()
            if not selection:
                break
            elif int(selection) < len(applications):
                apps.append(applications[int(selection)])
        except ValueError:
            pass
    ext_info["applications"] = apps

    #TODO: ask for path of icon file, and copy to files/icon.png

    with open(os.path.join(path, simple_name + ".json"), 'w+') as fp:
        json.dump(ext_info, fp, indent=4, separators=(',', ': '))
    print("Done!")

if __name__ == "__main__":
    main()