	var menupopup_0 = document.getElementById('{{menu_name}}');
	var menu_1 = document.getElementById('{{menu_id}}');
	if(menu_1) {
		var menupopup_2 = document.getElementById('{{menu_id}}-popup');
	} else {
		menu_1 = document.createElement('menu');
		menu_1.id = '{{menu_id}}';
		menu_1.classList.add('{{class}}');
		menu_1.setAttribute('label', buttonStrings.get('{{label}}'));
		var menupopup_2 = document.createElement('menupopup');
		menupopup_2.id = '{{menu_id}}-popup';
		menupopup_2.setAttribute('sortable', true);
		menupopup_2.addEventListener('popupshowing', function(event) {
			var item = event.target;
			{% if menuitems_sorted -%}
			toolbar_buttons.sortMenu(event, item);
			{% endif -%}
			toolbar_buttons.handelMenuLoaders(event, item);
		});
		menu_1.appendChild(menupopup_2);
		menupopup_0.insertBefore(menu_1, document.getElementById('{{insert_after}}').nextSibling);
	}