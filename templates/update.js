if(!this.load_{{ javascript_object }}) {
	var load_{{ javascript_object }} = {
		callbacks: [],
		
		start: function() {
			var version = "{{version}}";
			var prefService = Cc["@mozilla.org/preferences-service;1"].getService(Ci.nsIPrefService);
			var prefs = {{ javascript_object }}.interfaces.ExtensionPrefBranch;
			var currentVersion = prefs.getCharPref("{{current_version_pref}}");
			
			if(currentVersion != version){
				prefs.setCharPref("{{current_version_pref}}", version);
				prefService.savePrefFile(null);
				//load_{{ javascript_object }}.load_url(currentVersion, version);
				var callbacks = load_{{ javascript_object }}.callbacks;
				for(var i = 0; i < callbacks.length; i++) {
					load_{{ javascript_object }}.callbacks[i](currentVersion, version);
				}
			}
			window.removeEventListener("load", load_{{ javascript_object }}.start, false);
			
		},
		file_put_contents: function(file,data) {
			var foStream = {{ javascript_object }}.interfaces.FileOutputStream();
			foStream.init(file, 0x02 | 0x08 | 0x20, 0664, 0);
			foStream.write(data, data.length);
			foStream.close();
		},
		file_get_contents: function(file) {
			var data = '';
			var fstream = Cc['@mozilla.org/network/file-input-stream;1'].createInstance(Ci.nsIFileInputStream);
			var sstream = Cc['@mozilla.org/scriptableinputstream;1'].createInstance(Ci.nsIScriptableInputStream);
			fstream.init(file, -1, 0, 0);
			sstream.init(fstream); 		
			var str = sstream.read(4096);
			while (str.length > 0) {
				data += str;
				str = sstream.read(4096);
			}		
			sstream.close();
			fstream.close();
			return data;
		},
		load_url: function(previousVersion, currentVersion) {
			var url = "{{homepage_url}}updated/{{version}}/";
			if(previousVersion == "") {
				url = "{{homepage_url}}installed/{{version}}/";
			}
			try {
				window.getBrowser().selectedTab = window.getBrowser().addTab(url);
			} catch (e) {
				var uri = {{ javascript_object }}.interfaces.IOService.newURI(url, null, null);
				{{ javascript_object }}.interfaces.ExternalProtocolService.loadUrl(uri);
			}
		},
		add_buttons: function(buttons) {
			Cu.import("resource://modules/CustomizableUI.jsm");
			var toolbars = ['nav-bar', 'mail-bar3', 'composeToolbar2'];
			for(var i in toolbars) {
				if(document.getElementById(toolbars[i])) {
					for(var b in buttons) {
						CustomizableUI.addWidgetToArea(buttons[b], toolbars[i]);
					}
					return;
				}				
			}
		},
		observe: function(aSubject, aTopic, aData) {
			window.setTimeout(function() { load_{{ javascript_object }}.start(); }, 100);
		},
		restore: function() {
			window.setTimeout(function() { load_{{ javascript_object }}.start(); }, 100);
			document.removeEventListener("SSTabRestoring", load_{{ javascript_object }}.restore, false);
		}
	};
	try {
		var prefs = {{ javascript_object }}.interfaces.PrefBranch;
		if(prefs.getIntPref('browser.startup.page') == 3
			|| prefs.getBoolPref('browser.sessionstore.resume_session_once')) {
			//this observer never seems to run for some reason??
			//var observerService = Cc["@mozilla.org/observer-service;1"]
			//              .getService(Ci.nsIObserverService);
			//observerService.addObserver(load_{{ javascript_object }}, 'sessionstore-state-finalized', false);
			document.addEventListener("SSTabRestoring", load_{{ javascript_object }}.restore, false);
		} else {
			window.addEventListener("load", load_{{ javascript_object }}.start, false);
		}
	} catch(e) {
		window.addEventListener("load", load_{{ javascript_object }}.start, false);
	}
}
{%- if show_updated_prompt %}
load_{{ javascript_object }}.callbacks.push(load_{{ javascript_object }}.load_url);
{%- endif %}
{%- if add_to_main_toolbar %}
load_{{ javascript_object }}.callbacks.push(
	function(previousVersion, currentVersion) {
		if(previousVersion == '') {
			load_{{ javascript_object }}.add_buttons({{ buttons }});
		}
	});
{%- endif %}