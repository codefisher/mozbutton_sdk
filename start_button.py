#!/usr/bin/python

import os
import sys

from builder.util import apply_settings_files

try:
    from config import settings
except ImportError:
    print "Failed to load settings."
    sys.exit(1)

def main():
    args = sys.argv[1:]
    
    config = dict(settings.config)
    apply_settings_files(config, args)
    
    files = (
         ("fx", "browser"),
         ("tb", "messenger"),
         ("sb", "calendar"),
         ("b", "button"),
    )
    
    dfiles = dict(files)
    
    project = None
    
    print("Creating a new Toolbar Button\n")
    
    projects = config.get("projects")
    if len(projects) == 1:
        project = projects[0]
    else:
        print("Please select what project you want to add the button to.")
        for i, name in enumerate(projects):
            print("    [{0}] {1}".format(i, name))
        while True:
            try:
                selection = int(raw_input("Number: "))
                if selection < len(projects):
                    project = projects[selection]
                    break
            except ValueError:
                pass
    
    button_id = raw_input("What ID do you want to use: ").strip()
    label = raw_input("What label: ").strip()
    tooltip = raw_input("What tooltip: ").strip()
    description = raw_input("What description: ").strip()
    icon = raw_input("What icon: ").strip()
    
    button_id = config.get("new_button_prefix", "") + button_id
    
    print("Please select what application you want to support (you can add more later).")
    for i, name in files:
        print("    [{0}] {1}".format(i, name))
    while True:
        try:
            selection = raw_input("Application: ")
            if selection in dfiles:
                app = dfiles[selection]
                break
        except ValueError:
            pass
            
    try:
        os.mkdir(os.path.join(project, button_id))
    except:
        pass
    with open(os.path.join(project, button_id, 'image'), 'w+') as f:
        f.write(icon)
    with open(os.path.join(project, button_id, 'description'), 'w+') as f:
        f.write(description)
        
    with open(os.path.join(project, button_id, "strings"), 'w+') as strings:
        strings.write("%s.label=%s\n%s.tooltip=%s" % (button_id, label, button_id, tooltip))
    
    with open(os.path.join(project, button_id, "%s.xul" % app), 'w+') as xul:
        xul.write("""<toolbarbutton
	class="toolbarbutton-1 chromeclass-toolbar-additional"
	id="%s"
	label="&%s.label;"
	tooltiptext="&%s.tooltip;"
	oncommand=""/>""" % (button_id, button_id, button_id))

if __name__ == "__main__":
    main()
