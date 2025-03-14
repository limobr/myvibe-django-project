$(document).ready(function () {
    // Step navigation setup
    var navListItems = $('div.setup-panel div a'),
        allWells = $('.setup-content'),
        allNextBtn = $('.nextBtn');

    allWells.hide();

    navListItems.click(function (e) {
        e.preventDefault();
        var $target = $($(this).attr('href')),
            $item = $(this);

        if (!$item.hasClass('disabled')) {
            navListItems.removeClass('btn-success').addClass('btn-default');
            $item.addClass('btn-success');
            allWells.hide();
            $target.show();
            $target.find('input:eq(0)').focus();
        }
    });

    allNextBtn.click(function () {
        var curStep = $(this).closest(".setup-content"),
            curStepBtn = curStep.attr("id"),
            nextStepWizard = $('div.setup-panel div a[href="#' + curStepBtn + '"]').parent().next().children("a"),
            curInputs = curStep.find("input[type='text'], input[type='url'], input[type='number'], input[type='datetime-local'], textarea, select"),
            isValid = true;

        $(".form-group").removeClass("has-error");
        for (var i = 0; i < curInputs.length; i++) {
            if (!curInputs[i].validity.valid) {
                isValid = false;
                $(curInputs[i]).closest(".form-group").addClass("has-error");
            }
        }

        if (isValid) nextStepWizard.removeAttr('disabled').trigger('click');
    });

    $('div.setup-panel div a.btn-success').trigger('click');

    // Leaflet Map for Step 3
    var map, marker;

    // Initialize map when Step 3 is shown
    $('div.setup-panel div a[href="#step-3"]').on('click', function () {
        if (!map) {
            // Center on Kenya (approx coordinates: -1.286389, 36.817223)
            map = L.map('map').setView([-1.286389, 36.817223], 6); // Zoom level 6 shows Kenya well

            // Add OpenStreetMap tiles
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);

            // Add a draggable marker
            marker = L.marker([-1.286389, 36.817223], { draggable: true }).addTo(map);

            // Update form fields on marker drag
            marker.on('dragend', function (e) {
                var coords = e.target.getLatLng();
                $('input[name="latitude"]').val(coords.lat.toFixed(6));
                $('input[name="longitude"]').val(coords.lng.toFixed(6));
            });

            // Update form fields on map click
            map.on('click', function (e) {
                var coords = e.latlng;
                marker.setLatLng(coords);
                $('input[name="latitude"]').val(coords.lat.toFixed(6));
                $('input[name="longitude"]').val(coords.lng.toFixed(6));
            });

            // Set initial form values
            var initialCoords = marker.getLatLng();
            $('input[name="latitude"]').val(initialCoords.lat.toFixed(6));
            $('input[name="longitude"]').val(initialCoords.lng.toFixed(6));
        }
    });

    // Search bar functionality (now static in HTML)
    var searchInput = $('#location-search');
    var suggestionsDropdown = $('#suggestions');

    // Trigger search on input
    searchInput.on('input', function () {
        var query = $(this).val();
        if (query.length < 3) {
            suggestionsDropdown.hide();
            return;
        }

        $.ajax({
            url: 'https://nominatim.openstreetmap.org/search',
            data: {
                q: query + ', Kenya', // Restrict search to Kenya
                format: 'json',
                limit: 5,
                countrycodes: 'ke' // ISO code for Kenya
            },
            success: function (data) {
                suggestionsDropdown.empty();
                if (data.length > 0) {
                    data.forEach(function (place) {
                        var suggestion = $('<a class="dropdown-item" href="#">' + place.display_name + '</a>');
                        suggestion.on('click', function (e) {
                            e.preventDefault();
                            var lat = parseFloat(place.lat);
                            var lon = parseFloat(place.lon);
                            map.setView([lat, lon], 15); // Zoom in to selected location
                            marker.setLatLng([lat, lon]);
                            $('input[name="latitude"]').val(lat.toFixed(6));
                            $('input[name="longitude"]').val(lon.toFixed(6));
                            suggestionsDropdown.hide();
                            searchInput.val(place.display_name);
                        });
                        suggestionsDropdown.append(suggestion);
                    });
                    suggestionsDropdown.show();
                } else {
                    suggestionsDropdown.hide();
                }
            },
            error: function () {
                suggestionsDropdown.hide();
            }
        });
    });

    // Hide suggestions when clicking outside
    $(document).on('click', function (e) {
        if (!searchInput.is(e.target) && !suggestionsDropdown.is(e.target) && suggestionsDropdown.has(e.target).length === 0) {
            suggestionsDropdown.hide();
        }
    });
});