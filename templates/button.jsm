/*
 * This file was generated by the MozButton SDK,
 * which is part of the Toolbar Buttons project.
 * You should not edit this file, but rather download
 * the project source and rerun the builder.
 */

const Cc = Components.classes;
const Ci = Components.interfaces;
const Cu = Components.utils;

var EXPORTED_SYMBOLS = ["loadButtons", "unloadButtons", "setupButtons", "shutdownButtons"];

try {
	Cu.import("resource:///modules/CustomizableUI.jsm");
} catch(e) {
	Cu.import("chrome://{{chrome_name}}/content/customizable.jsm");
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
// the number at the end forces a reload of the properties file, since sometimes it it catched when we don't want
var buttonStrings = new StringBundle("chrome://{{chrome_name}}/locale/{{locale_file_prefix}}button_labels.properties?time=" + Date.now().toString());

function setupButtons() {
	var extensionPrefs = Cc['@mozilla.org/preferences-service;1'].getService(Ci.nsIPrefService).getBranch("{{pref_root}}");
	{%- for script in scripts %}
	loader.loadSubScript("chrome://{{chrome_name}}/content/{{script}}.js", gScope);
	{%- endfor %}
	// All these get wrapped in a try catch in case there is another button
	// with the same ID, which would throw an error.
	{{buttons}}
}

function loadButtons(window) {
	var document = window.document;
	var toolbox = document.getElementById('{{toolbox}}');
	if(!toolbox) {
		return;
	}
	var extensionPrefs = Cc['@mozilla.org/preferences-service;1'].getService(Ci.nsIPrefService).getBranch("extension.tbutton.");
	{{toolbars}}
	registerToolbars(window, document, {{toolbar_ids}});
	// we create the keys, then the menu items, so the menu items get connected to the keys
	{%- if keys %}
	var keyset = document.getElementById('mainKeyset');
	if(!keyset) {
		var keyset = document.createElement('keyset');
		keyset.id = 'mainKeyset';
		document.documentElement.appendChild(keyset);
	}
	function setKeyCode(key, keycode) {
		if(keycode.length == 1) {
			key.setAttribute('key', keycode);
			key.removeAttribute('keycode');
		} else {
			key.setAttribute('keycode', keycode);
			key.removeAttribute('key');
		}
	}
	function getLocalisedPref(name) {
		return extensionPrefs.getComplexValue(name, Ci.nsIPrefLocalizedString).data;
	}
	{%- for command, button in keys %}
	var key_{{loop.index}} = document.createElement('key');
	key_{{loop.index}}.id = '{{button}}-key';
	key_{{loop.index}}.setAttribute('oncommand', 'void(0);');
	key_{{loop.index}}.addEventListener('command', function(event) {
		{{command}}
	}, false);
	var key_disabled_{{loop.index}} = extensionPrefs.getBoolPref("key-disabled.{{button}}");
	key_{{loop.index}}.setAttribute('disabled', key_disabled_{{loop.index}});
	if(!key_disabled_{{loop.index}}) {
		setKeyCode(key_{{loop.index}}, getLocalisedPref("key.{{button}}"));
		key_{{loop.index}}.setAttribute('modifiers', getLocalisedPref("modifier.{{button}}"));
	}
	keyset.appendChild(key_{{loop.index}});
	{%- endfor %}
	function keyMove(key) {
		var keyset = key.parentNode;
		var root = keyset.parentNode;
		var newKeyset = document.createElement('keyset');
		root.appendChild(newKeyset);
		newKeyset.appendChild(key);
		var items = document.getElementsByAttribute('key', key.id);
		for(var i = 0; i < items.length; ++i) {
			var item = items[i];
			item.removeAttribute('key');
			item.setAttribute('key', key.id);
		}
		if(keyset.childNodes.length == 0) {
			keyset.parentNode.removeChild(keyset);
		}
	}
	var keyWatcher = new toolbar_buttons.settingWatcher('{{pref_root}}key.', function(subject, topic, data) {
		var key = document.getElementById(data + '-key');
		var keycode = getLocalisedPref("key." + data);
		setKeyCode(key, keycode);
		keyMove(key);
	});
	keyWatcher.startup();
	var modifiersWatcher = new toolbar_buttons.settingWatcher('{{pref_root}}modifier.', function(subject, topic, data) {
		var key = document.getElementById(data + '-key');
		var modifiers = getLocalisedPref("modifier." + data);
		key.setAttribute('modifiers', modifiers);
		keyMove(key);
	});
	modifiersWatcher.startup();
	var keyDisabledWatcher = new toolbar_buttons.settingWatcher('{{pref_root}}key-disabled.', function(subject, topic, data) {
		var key = document.getElementById(data + '-key');
		var disabled = extensionPrefs.getBoolPref('key-disabled.' + data)
		key.setAttribute('disabled', disabled);
		if(disabled) {
			key.removeAttribute('keycode');
			key.removeAttribute('key');
			key.removeAttribute('modifiers');
		} else {
			setKeyCode(key, getLocalisedPref("key." + data));
			key.setAttribute('modifiers', getLocalisedPref("modifier." + data));
		}
		keyMove(key);
	});
	keyDisabledWatcher.startup();
	{%- endif %}
	{{menu}}
	{{end}}
}

function createToolbar(doc, toolbox, attributes, name) {
	var special = ["id", "class", "defaultset", "currentset"];
	var toolbar = doc.createElement('toolbar');
	for(var attr in attributes) {
		if(special.indexOf(attr) == -1) {
			toolbar.setAttribute(attr, attributes[attr]);
		}
	}
	toolbar.setAttribute('toolbarname', name);
	if(attributes.id) {
		toolbar.id = attributes.id;
	}
	if(attributes.class) {
		toolbar.className = attributes.class;
	}
	doc.getElementById(toolbox).appendChild(toolbar);
	// put after appending to stop Thunderbird/SeaMonkey loading the buttons
	// which messes with our CustomizableUI
	if(attributes.defaultset) {
		toolbar.setAttribute('defaultset', attributes['defaultset']);
	}
	if(attributes.currentset) {
		toolbar.setAttribute('currentset', attributes['currentset']);
	}
}

var gButtonIds = {{button_ids}};

function unloadButtons(window) {
	var document = window.document;
	var toolbarIds = {{toolbar_ids}};
	var uiIds = {{ui_ids}};

	for(var t = 0; t < toolbarIds.length; t++) {
		var toolbar = document.getElementById(toolbarIds[t]);
		if(toolbar) {
			CustomizableUI.unregisterArea(toolbarIds[t], false);
			toolbar.parentNode.removeChild(toolbar);
		}
	}
	for(var i = 0; i < gButtonIds.length; i++) {
		var buttonId = gButtonIds[i];
		var key = document.getElementById(buttonId + '-key');
		if(key) {
			key.parentNode.removeChild(key);
			//if(key.parentNode.childNodes.length == 0) {
			//	key.parentNode.parentNode.removeChild(key.parentNode);
			//}
		}
		var menuitem = document.getElementById(buttonId + '-menu-item');
		if(menuitem) {
			menuitem.parentNode.removeChild(menuitem);
		}
	}
	var menu = document.getElementById('{{menu_id}}');
	if(menu && !menu.firstChild.firstChild) {
		menu.parentNode.removeChild(menu);
	}
	for(var i = 0; i < uiIds.length; i++) {
		var node = document.getElementById(uiIds[i]);
		while(node) {
			node.parentNode.removeChild(node);
			node = document.getElementById(uiIds[i]);
		}
	}
	for(var i = 0; i < gShutDownFunctions.length; i++) {
		try {
			gShutDownFunctions[i]();
		} catch(e) {}
	}
}

function shutdownButtons() {
	log(gButtonIds);
	for(var i = 0; i < gButtonIds.length; i++) {
		CustomizableUI.destroyWidget(gButtonIds[i]);
	}
}

function registerToolbars(window, document, toolbar_ids) {
	for(var i in toolbar_ids) {
		observeToolbar(window, document, toolbar_ids[i]);
		CustomizableUI.registerArea(toolbar_ids[i], {
			type: CustomizableUI.TYPE_TOOLBAR,
			defaultPlacements: [],
			defaultCollapsed: false
		}, true);
	}
}

function observeToolbar(window, document, toolbar_id) {
	var prefs = Cc['@mozilla.org/preferences-service;1'].getService(Ci.nsIPrefService)
			.getBranch("{{pref_root}}" + 'toolbar_status.' + toolbar_id + '.');
	var toolbar = document.getElementById(toolbar_id);
	var observer = function(mutations) {
		mutations.forEach(function(mutation) {
			if(mutation.attributeName && (CustomizableUI.shim || mutation.attributeName != 'currentset')) {
				prefs.setCharPref(mutation.attributeName, toolbar.getAttribute(mutation.attributeName));
			}
		});
	};
	var mutationObserver = new window.MutationObserver(observer);
	var attrList = prefs.getChildList('', {});
	for(var i in attrList) {
		toolbar.setAttribute(attrList[i], prefs.getCharPref(attrList[i]));
	}
	mutationObserver.observe(toolbar, { attributes: true, subtree: false });
}

function log(e) {
	Cc["@mozilla.org/consoleservice;1"].getService(Ci.nsIConsoleService).logStringMessage(e);
}