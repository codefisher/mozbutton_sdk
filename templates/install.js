	var prefService = Cc['@mozilla.org/preferences-service;1'].getService(Ci.nsIPrefService);
	var prefs = prefService.getBranch("{{pref_root}}");
	var version = "{{version}}";
	var currentVersion = prefs.getCharPref("{{current_version_pref}}");
	var url = "{{homepage}}updated/{{version}}/";
	if(currentVersion == "") {
		url = "{{homepage}}installed/{{version}}/";
	}
	if(currentVersion != version) {
		prefs.setCharPref("{{current_version_pref}}", version);
		prefService.savePrefFile(null);
		let wm = Cc["@mozilla.org/appshell/window-mediator;1"].getService(Ci.nsIWindowMediator);
		let win =  wm.getMostRecentWindow("navigator:browser");
		if(win) {
			let domWindow = win.QueryInterface(Ci.nsIDOMWindow);
			if(win.document.readyState === "complete") {
				/* domWindow.getBrowser().selectedTab = */ domWindow.getBrowser().addTab(url);
			} else {
				domWindow.addEventListener("load", function startPageLoad() {
					domWindow.getBrowser().selectedTab = domWindow.getBrowser().addTab(url);
					domWindow.removeEventListener("load", startPageLoad, false);
				}, false);
			}
		} else {
			let win = wm.getMostRecentWindow(null);
			if(win) {
				var uri = Cc['@mozilla.org/network/io-service;1'].getService(Ci.nsIIOService).newURI(url, null, null);
				Cc['@mozilla.org/uriloader/external-protocol-service;1'].getService(Ci.nsIExternalProtocolService).loadUrl(uri);
			} else {
				var windowListener = {
					onOpenWindow: function (aWindow) {
						let domWindow = aWindow.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIDOMWindowInternal || Ci.nsIDOMWindow);
						domWindow.addEventListener("load", function onLoad() {
							domWindow.removeEventListener("load", onLoad, false);
							wm.removeListener(windowListener);
							try {
								var opened = false;
								var prefs = Cc['@mozilla.org/preferences-service;1'].getService(Ci.nsIPrefBranch);
								if(prefs.getIntPref('browser.startup.page') == 3 || prefs.getBoolPref('browser.sessionstore.resume_session_once')) {
									domWindow.document.addEventListener("SSTabRestoring", function tabRestored() {
										domWindow.document.addEventListener("SSTabRestoring", tabRestored, false);
										if(!opened) { // can't work out why it gets called mutiple times
											domWindow.getBrowser().addTab(url);
											opened = true;
										}
									}, false);
								} else {
									domWindow.getBrowser().addTab(url);
								}
							} catch(e) {
								var uri = Cc['@mozilla.org/network/io-service;1'].getService(Ci.nsIIOService).newURI(url, null, null);
								Cc['@mozilla.org/uriloader/external-protocol-service;1'].getService(Ci.nsIExternalProtocolService).loadUrl(uri);
							}
						}, false);
					},
					onCloseWindow: function (aWindow) {
					},
					onWindowTitleChange: function (aWindow, aTitle) {
					}
				};
				wm.addListener(windowListener);
			}
		}
	}