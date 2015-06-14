import getopt
import sys
import textwrap
import time
import os

from builder.build import build_extension, apply_max_version
from builder.screenshot import create_screenshot
from builder.util import apply_settings_files, get_svn_revision, get_git_revision, create_update_rdf

try:
    from config import settings
except ImportError:
    print("Failed to load settings.")
    sys.exit(1)

try:
    raw_input
except NameError:
    raw_input = input

def main():
    opts, args = getopt.getopt(sys.argv[1:], "pvb:l:a:o:f:s:m:", 
        ["help", "profile", "screen-shot", "icons-per-row=", "screen-shot-font=", 
            "git-revision", "lookup-max-versions", "svn-revision", "update-rdf="])
    opts_table = dict(opts)
    if "--help" in opts_table:
        print(textwrap.dedent("""
        MozButton SDK

            -b    - a button to inlcude
            -a    - an application to include
            -l    - a locale to include
            -o    - the folder to put the created extension in
            -f    - the file name for the created extension
            -s    - the sizes to use for the icons, must be two numbers separated
                        by a hyphen.
            -m    - merge all images into single large image, either y or n
            -p    - prompt for a list of config files to build extensions for
            
            -v --lookup-max-versions 
                  - do a web lookup of the latest application versions, and apply that to 
                    settings used to build the extension
                    
            --git-revision       - add the git revision number to the version
            --svn-revision       - add the svn revision number to the version
            
            --update-rdf=        - create an update rdf file for the extension and save the the given file

            --profile            - output profiling data 
            --screen-shot        - a fake screen shot of all the buttons in the extension
            --icons-per-row=     - the number of icons to put on each row of the screen shot
            --screen-shot-font=  - the file to the font to use for the window title
        """).strip())
        return
    config = dict(settings.config)
    apply_settings_files(config, args)
    if "--lookup-max-versions" in opts_table or "-v" in opts_table:
        apply_max_version(config)
    if "--git-revision" in opts_table:
        config["version"] = "{}.r{}".format(config["version"], get_git_revision(config))
    if "--svn-revision" in opts_table:
        config["version"] = "{}.r{}".format(config["version"], get_svn_revision(config))
    if "--update-rdf" in opts_table:
        with open(os.path.join(config.get("project_root"), config.get("output_folder"), opts_table["--update-rdf"]), "w") as rdf_fp:
            rdf_fp.write(create_update_rdf(config))
    for name, setting in (("-b", "buttons"), ("-l", "locale"), ("-a", "applications")):
        if name in opts_table:
            config[setting] = [value for arg, value in opts if arg == name]
    if "-o" in opts_table:
        config["output_folder"] = opts_table["-o"]
    if "-f" in opts_table:
        config["output_file"] = opts_table["-f"]
    if "-s" in opts_table:
        config["icon_size"] = tuple(opts_table["-s"].split('-'))
    if "-m" in opts_table:
        config["merge_images"] = opts_table["-m"].lower() == "y"
    start = time.time()
    if "-p" in opts_table:
        for file in raw_input().split():
            lconfig = dict(config)
            apply_settings_files(lconfig, [file])
            build_extension(lconfig)
    elif "--screen-shot" in opts_table:
        if "--icons-per-row" in opts_table:
            config["icons_per_row"] = int(opts_table["--icons-per-row"])
        if "--screen-shot-font" in opts_table:
            config["screen_shot_font"] = opts_table["--screen-shot-font"]
        create_screenshot(config)
        return
    elif "--profile" in opts_table:
        import cProfile
        import pstats
        cProfile.runctx("build_extension(settings)",
                    {"build_extension": build_extension, "settings": config}, {},
                    "./stats")
        prof = pstats.Stats("./stats")
        prof.sort_stats('cumulative') # time, cumulative
        prof.print_stats()
    else:
        build_extension(config)
    print(time.time() - start)

if __name__ == "__main__":
    main()
