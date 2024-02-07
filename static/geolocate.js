/*
  Source: https://james-priest.github.io/100-days-of-code-log-r2/CH14-Geolocation.html
  + others
 */

var watchId = 0;
var lastUpdateTime;
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
  showMessage(
    'Latitude: ' + position.coords.latitude + '<br>' +
    'Longitude: ' + position.coords.longitude + '<br>' +
    'Timestamp: ' + datetime
  );
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

