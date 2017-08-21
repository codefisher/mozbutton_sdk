import getopt
import sys

from builder.build import build_extension, create_objects, ExtensionConfigError
from builder.util import apply_settings_files

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
    opts, args = getopt.getopt(sys.argv[1:], "", [])

    config = dict(settings.config)
    apply_settings_files(config, args)

    buttons_set = set()

    for file in raw_input().split():
        lconfig = dict(config)
        apply_settings_files(lconfig, [file])
        buttons_set.update(lconfig.get("buttons"))
    config["applications"] = ["browser"]
    button_locales, buttons, locales = create_objects(config)

    print set(buttons.buttons()).difference(buttons_set)


if __name__ == "__main__":
    main()
