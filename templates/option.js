toolbar_buttons.toolbar_button_loader(toolbar_buttons, {
	%s
});
%s

var keypresser = {
	os: Components.classes["@mozilla.org/xre/app-info;1"]
                   .getService(Components.interfaces.nsIXULRuntime).OS,
	prefs: toolbar_buttons.interfaces.ExtensionPrefBranch,
	display: function(modifiersString, keyString) {
		var keys = [];
		var modifiers = modifiersString.split(',');
		let os = keypresser.os;
		for (let i = 0; i < modifiers.length; i++) {
			switch (modifiers[i]) {
				case 'control':
					keys.push(os == "Darwin" ? 'control' : 'Ctrl');
					break;
				case 'ctrl':
					keys.push(os == "Darwin" ? 'control' : 'Ctrl');
					break;
				case 'shift':
					keys.push(os == "Darwin" ? 'shift' : 'Shift');
					break;
				case 'alt':
					keys.push(os == "Darwin" ? 'option' : 'Alt');
					break;
				case 'meta':
					keys.push(os == "Darwin" ? 'command' : 'Meta');
					break;
				case 'accel':
					keys.push(os == "Darwin" ? 'command' : 'Ctrl');
					break;
				case 'os':
					keys.push(os == "Darwin" ? 'Win' : 'Win');
					break;
			}
		}
		keys.push(keyString.replace('VK_', ''));
		return keys.join(' + ');
	},
	setup: function(node) {
		var key = keypresser.prefs.getComplexValue("key." + node.getAttribute('button'),
						Ci.nsIPrefLocalizedString).data;
		var modifier = keypresser.prefs.getComplexValue("modifier." + node.getAttribute('button'),
						Ci.nsIPrefLocalizedString).data;
		node.value = keypresser.display(modifier, key);
	},
	keycodes: {
		'ARROWDOWN': 'VK_DOWN',
		'ARROWUP': 'VK_UP',
		'ARROWLEFT': 'VK_LEFT',
		'ARROWRIGHT': 'VK_RIGHT',
		'PAGEDOWN': 'VK_PAGE_DOWN',
		'PAGEUP': 'VK_PAGE_UP'
	},
	keypress: function(event) {
		var node = event.target;
		var modifiers = [];
		var hotkey = event.key.toUpperCase();
		if(hotkey.length != 1) {
			if(keypresser.keycodes[hotkey]) {
				hotkey = keypresser.keycodes[hotkey];
			} else {
				hotkey = 'VK_' + hotkey;
			}
		}
		if(event.metaKey) {
			modifiers.push('meta');
		}
		if(event.ctrlKey) {
			modifiers.push('ctrl');
		}
		if(event.altKey) {
			modifiers.push('alt');
		}
		if(event.shiftKey) {
			modifiers.push('shift');
		}
		modifiers = modifiers.join(',');

		node.value = keypresser.display(modifiers, hotkey);
		keypresser.prefs.setCharPref("key." + node.getAttribute('button'), hotkey);
		keypresser.prefs.setCharPref("modifier." + node.getAttribute('button'), modifiers);

		event.preventDefault();
		event.stopPropagation();
	}
};

window.addEventListener('load', function() {
	if(window.arguments && window.arguments.length) {
		window.document.documentElement.showPane(document.getElementById(window.arguments[0]));
	}
	var keyboxes = document.getElementsByAttribute('use', 'keycode');
	for(var i = 0; i < keyboxes.length; ++i) {
		keypresser.setup(keyboxes[i]);
		keyboxes[i].addEventListener('keypress', keypresser.keypress, false);
	}
}, false);