var keyset = document.getElementById('mainKeyset');
	if(!keyset) {
		var keyset = document.createElement('keyset');
		keyset.id = 'mainKeyset';
		document.documentElement.appendChild(keyset);
	}
	{{keys}}
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
		var keycode = extensionPrefs.getComplexValue("key." + data, Ci.nsIPrefLocalizedString).data;
		if(keycode.length == 1) {
			key.setAttribute('key', keycode);
			key.removeAttribute('keycode');
		} else {
			key.setAttribute('keycode', keycode);
			key.removeAttribute('key');
		}
		keyMove(key);
	});
	keyWatcher.startup();
	var modifiersWatcher = new toolbar_buttons.settingWatcher('{{pref_root}}modifier.', function(subject, topic, data) {
		var key = document.getElementById(data + '-key');
		var modifiers = extensionPrefs.getComplexValue("modifier." + data, Ci.nsIPrefLocalizedString).data;
		key.setAttribute('modifiers', modifiers);
		keyMove(key);
	});
	modifiersWatcher.startup();
	var keyDisabledWatcher = new toolbar_buttons.settingWatcher('{{pref_root}}key-disabled.', function(subject, topic, data) {
		var key = document.getElementById(data + '-key');
		key.setAttribute('disabled', extensionPrefs.getBoolPref('key-disabled.' + data));
		keyMove(key);
	});
	keyDisabledWatcher.startup();