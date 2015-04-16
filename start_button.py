import os
import sys
import re

from builder.util import apply_settings_files

try:
    from config import settings
except ImportError:
    print("Failed to load settings.")
    sys.exit(1)
    
def function_name(match):
    return match.group(1).upper()

def main():
    args = sys.argv[1:]
    
    config = dict(settings.config)
    apply_settings_files(config, args)
    
    files = (
         ("fx", "browser"),
         ("tb", "messenger"),
         ("sb", "calendar"),
         ("sm", "suite_browser"),
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
    function = re.sub(r"[^a-zA-Z]+([a-zA-Z])", function_name, button_id)
    label = raw_input("What label: ").strip()
    tooltip = raw_input("What tooltip: ").strip()
    description = raw_input("What description: ").strip()
    icon = raw_input("What icon: ").strip()
    button_id = config.get("new_button_prefix", "") + button_id
    
    print("Please select what application you want to support (you can add more later).\nPress enter to finish.")
    for i, name in files:
        print("    [{0}] {1}".format(i, name))
    apps = []
    while True:
        try:
            selection = raw_input("Application: ").strip()
            if selection in dfiles:
                apps.append(dfiles[selection])
            elif not selection:
                break
        except ValueError:
            pass
    
    add_script = raw_input("Do you want to add a script file? Y/N: ")
    add_js = (add_script and add_script[0].lower() == "y")
    
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
    
    for app in apps:
        if add_js:
            with open(os.path.join(project, button_id, "%s.js" % app), 'w+') as js:
                js.write("""%s: function() {\n}\n""" % function)
        with open(os.path.join(project, button_id, "%s.xul" % app), 'w+') as xul:
            xul.write("""<toolbarbutton
	class="toolbarbutton-1 chromeclass-toolbar-additional"
	id="%s"
	label="&%s.label;"
	tooltiptext="&%s.tooltip;"
	oncommand=""/>""" % (button_id, button_id, button_id))

if __name__ == "__main__":
    main()
