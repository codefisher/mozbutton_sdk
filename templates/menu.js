	var menupopup_0 = document.getElementById('%(menu_name)s');
	var menu_1 = document.getElementById('%(menu_id)s');
	if(menu_1) {
		var menupopup_2 = document.getElementById('%(menu_id)s-popup');
	} else {
		menu_1 = document.createElement('menu');
		menu_1.id = '%(menu_id)s';
		menu_1.classList.add('%(class)s');
		menu_1.setAttribute('label', buttonStrings.get('%(label)s'));
		var menupopup_2 = document.createElement('menupopup');
		menupopup_2.id = '%(menu_id)s-popup';
		menupopup_2.setAttribute('sortable', true);
		menupopup_2.addEventListener('popupshowing', function(event) {
			var item = event.target;
			toolbar_buttons.sortMenu(event, item);
			toolbar_buttons.handelMenuLoaders(event, item);
		});
		menu_1.appendChild(menupopup_2);
		menupopup_0.insertBefore(menu_1, document.getElementById('%(insert_after)s').nextSibling);
	}