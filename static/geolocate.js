/*
  Source: https://james-priest.github.io/100-days-of-code-log-r2/CH14-Geolocation.html
  + others
 */

var watchId = 0;
var lastUpdateTime;
var lastGeohash = "";
var minFrequency = 5*1000;

function supportsGeolocation() {
  return 'geolocation' in navigator;
}

function showMessage(message) {
  $('#message').html(message);
}

function getLocation() {
  if (supportsGeolocation()) {
    var options = { enableHighAccuracy: true };
    watchId = navigator.geolocation.watchPosition(onSuccess, showError, options);
  } else {
    showMessage("Geolocation isn't supported by your browser");
  }
}

function endWatch() {
  if (watchId != 0) {
    navigator.geolocation.clearWatch(watchId);
    watchId = 0;
    showMessage("Monitoring ended.");
  }
}

function setGeoMonitor(cb) {
  if (cb.checked) {
    getLocation();
  } else {
    endWatch();
  }
}

function onSuccess(position) {
  var now = new Date();
  if(lastUpdateTime && (now.getTime() - lastUpdateTime.getTime() < minFrequency)) {
    console.log("Ignoring position update");
    return;
  }
  lastUpdateTime = now;
  var datetime = new Date(position.timestamp).toLocaleString();
  var curLat = position.coords.latitude;
  var curLon = position.coords.longitude;
  /*
    9 chars => +/- 2.4 meters
    8 chars => +/- 19 meters
   */
  var curGeohash = encodeGeoHash(curLat, curLon).substring(0, 8);
  console.log("Geohash: " + curGeohash);
  showMessage(
    'Lat: ' + curLat + '<br>'
    + 'Lon: ' + curLon + '<br>'
    + datetime
  );
  if(lastGeohash == curGeohash) {
    console.log("Geohash hasn't changed");
    return;
  }
  lastGeohash = curGeohash;
  // Move map to this (lat, lon)
  var pt = L.latLng(curLat, curLon);
  mymap.setView(pt, zoom);
}

function showError(error) {
  switch (error.code) {
    case error.PERMISSION_DENIED:
      showMessage("User denied Geolocation access request.");
      break;
    case error.POSITION_UNAVAILABLE:
      showMessage("Location Information unavailable.");
      break;
    case error.TIMEOUT:
      showMessage("Get user location request timed out.");
      break;
    case error.UNKNOWN_ERROR:
      showMessage("An unknown error occurred.");
      break;
  }
}

/*
  This relies on leaflet.js having been pulled into the HTML page and also
  mymap having been defined.
 */
var command = L.control({position: 'topleft'});
command.onAdd = function (mymap) {
  var div = L.DomUtil.create('div', 'command');
  div.innerHTML =
    '<form>'
    + '<input id="command" type="checkbox" onchange="setGeoMonitor(this)"/>'
    + '<b>Enable realtime location?</b>'
    + '</form>'
    + '<div id="message"></div>';
  return div;
};
command.addTo(mymap);

