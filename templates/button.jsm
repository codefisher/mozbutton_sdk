const Cc = Components.classes;
const Ci = Components.interfaces;
const Cu = Components.utils;

var EXPORTED_SYMBOLS = ["loadButtons", "unloadButtons"];
var usingCustomizableUI = true;

try {
	Cu.import("resource:///modules/CustomizableUI.jsm");
} catch(e) {
	usingCustomizableUI = false;
	var CustomizableUIs = {};
	var CustomizableUI = null;
	Cu.import("chrome://{{chrome-name}}/content/customizable.jsm");
}

Cu.import('resource://gre/modules/Services.jsm');
Cu.import("resource://services-common/stringbundle.js");
{{modules}}

var gShutDownFunctions = [];

var toolbar_buttons = {
	interfaces: {},
	// the important global objects used by the extension
	toolbar_button_loader: function(parent, child) {
		var object_name;
		for(object_name in child){
			if(object_name == 'interfaces') {
				toolbar_buttons.toolbar_button_loader(parent.interfaces, child.interfaces);
			} else {
				parent[object_name] = child[object_name];
			}
		}
	},
	registerCleanUpFunction: function(func) {
		gShutDownFunctions.push(func);
	}

};
var loader = Cc["@mozilla.org/moz/jssubscript-loader;1"].getService(Ci.mozIJSSubScriptLoader);
var gScope = this;

function loadButtons(window) {
	var toolbox = window.document.getElementById('{{toolbox}}');
	if(!toolbox) {
		return;
	}
	var document = window.document;
	var scope = Object.create(gScope);
	scope.window = window;
	scope.document = document;

	if(!usingCustomizableUI) { //this is out own hacked up version
		CustomizableUI = new customizableUI(toolbox);
		CustomizableUIs[window] = CustomizableUI;
	}
	let buttonStrings = new StringBundle("chrome://{{chrome-name}}/locale/{{locale-file-prefix}}button_labels.properties");
	{{scripts}}
		
	{{toolbars}}
	registerToolbars(window, document, {{toolbar_ids}});
	
{{buttons}}

	{{menu}}
	
	{{keys}}
	
	{{end}}
}

function unloadButtons(window) {
	var document = window.document;
	var button_ids = {{button_ids}};
	var toolbar_ids = {{toolbar_ids}};
	var ui_ids = {{ui_ids}};
	if(!usingCustomizableUI) { //this is out own hacked up version
		CustomizableUI = CustomizableUIs[window];
		delete CustomizableUIs[window];
	}
	for(var i = 0; i < button_ids.length; i++) {
		var button_id = button_ids[i];
		CustomizableUI.destroyWidget(button_id);
		var key = document.getElementById(button_id + '-key');
		if(key) {
			key.parentNode.removeChild(key);
		}
		var menuitem = document.getElementById(button_id + '-menu-item');
		if(menuitem) {
			menuitem.parentNode.removeChild(menuitem);
		}
	}
	var menu = document.getElementById('{{menu_id}}');
	if(menu && !menu.firstChild.firstChild) {
		menu.parentNode.removeChild(menu);
	}
	for(var t = 0; t < toolbar_ids.length; t++) {
		var toolbar = document.getElementById(toolbar_ids[t]);
		if(toolbar) {
			toolbar.parentNode.removeChild(toolbar);
			CustomizableUI.unregisterArea(toolbar_ids[t], false);
		}
	}
	for(var i = 0; i < ui_ids.length; i++) {
		var node = document.getElementById(ui_ids[i]);
		while(node) {
			node.parentNode.removeChild(node);
			var node = document.getElementById(ui_ids[i]);
		}
	}
	for(var i = 0; i < gShutDownFunctions.length; i++) {
		try {
			gShutDownFunctions[i]();
		} catch(e) {}
	}
}

function registerToolbars(window, document, toolbar_ids) {
	if(!usingCustomizableUI) { //this is out own hacked up version
		CustomizableUI = CustomizableUIs[window];
	}
	for(var i in toolbar_ids) {
		observeToolbar(toolbar_ids[i]);
		CustomizableUI.registerArea(toolbar_ids[i], {
			type: CustomizableUI.TYPE_TOOLBAR,
			defaultPlacements: [],
			defaultCollapsed: false
		}, true);
	}
}

function observeToolbar(toolbar_id) {
	var prefs = Cc['@mozilla.org/preferences-service;1'].getService(Ci.nsIPrefService)
			.getBranch("{{pref_root}}" + 'toolbar_status.' + toolbar_id + '.');
	var toolbar = document.getElementById(toolbar_id);
	var mutationObserver = new window.MutationObserver(function(mutations) {
		mutations.forEach(function(mutation) {
			if(mutation.attributeName && (!usingCustomizableUI || mutation.attributeName != 'currentset')) {
				prefs.setCharPref(mutation.attributeName, toolbar.getAttribute(mutation.attributeName));
			}
		});
	});
	var attrList = prefs.getChildList('', {});
	for(var i in attrList) {
		toolbar.setAttribute(attrList[i], prefs.getCharPref(attrList[i]));
	}
	mutationObserver.observe(toolbar, { attributes: true, subtree: false });
}