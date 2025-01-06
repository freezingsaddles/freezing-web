// https://mokole.com/palette.html - 25 / 20% / 80% / 5000
// const track_colors = [
// 	'#c0c0c0', '#2f4f4f', '#556b2f', '#800000', '#483d8b',
// 	'#3cb371', '#000080', '#9acd32', '#8b008b', '#ff0000',
// 	'#00ced1', '#ffa500', '#ffff00', '#7fff00', '#8a2be2',
// 	'#00ff7f', '#00bfff', '#0000ff', '#ff7f50', '#ff00ff',
// 	'#1e90ff', '#db7093', '#f0e68c', '#ff1493', '#ee82ee',
// ];
// https://observablehq.com/@shan/oklab-color-wheel - .65 / 26 / 2 / 0 / .29
const track_colors = [
  'rgb(255, 0, 0)', 'rgb(255, 49, 0)', 'rgb(246, 83, 0)', 'rgb(224, 109, 0)', 'rgb(195, 132, 0)',
  'rgb(157, 151, 0)', 'rgb(106, 166, 0)', 'rgb(0, 178, 0)', 'rgb(0, 186, 3)', 'rgb(0, 191, 99)',
  'rgb(0, 191, 150)', 'rgb(0, 188, 194)', 'rgb(0, 180, 232)', 'rgb(0, 169, 255)', 'rgb(0, 154, 255)',
  'rgb(0, 137, 255)', 'rgb(33, 119, 255)', 'rgb(112, 101, 255)', 'rgb(153, 83, 255)', 'rgb(185, 65, 255)',
  'rgb(212, 44, 252)', 'rgb(234, 10, 218)', 'rgb(252, 0, 179)', 'rgb(255, 0, 136)', 'rgb(255, 0, 87)',
];
function create_ride_map(id, url, ride_color = null, recenter = false) {
  const map = L.map(id, { scrollWheelZoom: false }).setView([38.9072, -77.0369], 9);
  const colorMode = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  var tiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/' + colorMode + '_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20,
  }).addTo(map);
  fetch(url).then(r => r.json()).then(data => {
    if (recenter) {
      let minlat = 90, maxlat = -90, minlon = 180, maxlon = -180;
      for (const { track } of data.tracks) {
        for (const [lat, lon] of track) {
          if (lat < minlat) minlat = lat; else if (lat > maxlat) maxlat = lat;
          if (lon < minlon) minlon = lon; else if (lon > maxlon) maxlon = lon;
        }
      }
      if (minlat < maxlat) {
        const bounds = new L.LatLngBounds([[maxlat, maxlon], [minlat, minlon]]);
        map.fitBounds(bounds, {padding: [20, 20]});
      }
    }
    data.tracks.forEach(({ team, track}, index) => {
      const color = ride_color ?? track_colors[team % track_colors.length];
      const opacity = .2 + .4 * (index + 1) / data.tracks.length;
      var polyline = L.polyline([track], { color, opacity, weight: 2 }).addTo(map);
    });
  });
}
