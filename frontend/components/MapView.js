"use client";

import { MapContainer, TileLayer, Marker, Popup, Polyline, CircleMarker, Circle, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import styles from "./MapView.module.css";
import { useLocale } from "@/lib/i18n/LocaleContext";

// Leaflet's default marker icon paths are resolved relative to the bundler
// output and break under Next.js -- point them at the CDN copies instead.
const pinIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const DEFAULT_CENTER = { lat: 13.0827, lon: 80.2707 }; // Chennai, fallback only

// Bridges Leaflet's native click event out to React -- must be a child of
// MapContainer (react-leaflet's hooks only work inside the map context).
function ClickHandler({ onLocationClick }) {
  useMapEvents({
    click(e) {
      onLocationClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

const COLOR = {
  pfz: "#16a34a",
  hazard: "#dc2626",
  route: "#2a6fdb",
  boundary: "#5b6b83",
  location: "#2a6fdb",
  gps: "#7c3aed",
};

/**
 * @param {object} props
 * @param {object|null} [props.mapData]   - Data returned from a query response.
 * @param {object|null} [props.layers]    - Static map layer data.
 * @param {object}      [props.visibility]
 * @param {boolean}     [props.interactive]
 * @param {{lat:number,lon:number}|null} [props.gpsCenter] - Live GPS position (lat/lon).
 * @param {(lat: number, lon: number) => void} [props.onLocationClick] - Called when the user clicks the map.
 * @param {{lat:number,lon:number}|null} [props.pendingPoint] - A just-clicked point still waiting on its query response.
 */
export default function MapView({
  mapData,
  layers,
  visibility = {},
  interactive = true,
  gpsCenter = null,
  onLocationClick = null,
  pendingPoint = null,
}) {
  const { t } = useLocale();

  // Center priority: query/click response > live GPS > static mock layers > Chennai default.
  // (The backend's map_data never actually sets a "center" field -- only
  // current_position -- so that used to be checked first, which meant this
  // always fell through to the mock layers' hardcoded Chennai center even
  // when real GPS or a clicked point was available.)
  const center = mapData?.current_position ?? gpsCenter ?? layers?.center ?? DEFAULT_CENTER;
  const zoom = mapData?.zoom ?? layers?.zoom ?? 9;

  // Show a GPS marker only when we have a live position AND the query hasn't
  // already provided a current_position (to avoid double-pinning).
  const showGpsMarker = gpsCenter && !mapData?.current_position;

  return (
    <div className={styles.wrap}>
      <MapContainer
        key={`${center.lat}-${center.lon}-${zoom}`}
        center={[center.lat, center.lon]}
        zoom={zoom}
        zoomControl={interactive}
        dragging={interactive}
        scrollWheelZoom={interactive}
        doubleClickZoom={interactive}
        touchZoom={interactive}
        boxZoom={interactive}
        keyboard={interactive}
        attributionControl={interactive}
        className={`${styles.map} ${interactive && onLocationClick ? styles.clickable : ""}`}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {interactive && onLocationClick && <ClickHandler onLocationClick={onLocationClick} />}

        {pendingPoint && (
          <CircleMarker
            center={[pendingPoint.lat, pendingPoint.lon]}
            radius={9}
            pathOptions={{ color: COLOR.location, fillOpacity: 0.3, weight: 2, dashArray: "3 4" }}
            className={styles.pendingPin}
          />
        )}

        {visibility.pfz &&
          layers?.pfzZones?.map((z) => (
            <CircleMarker key={z.id} center={[z.lat, z.lon]} radius={9} pathOptions={{ color: COLOR.pfz, fillOpacity: 0.55, weight: 2 }}>
              <Popup>{z.id}</Popup>
            </CircleMarker>
          ))}

        {visibility.hazard &&
          layers?.hazardZones?.map((hz) => (
            <Circle
              key={hz.id}
              center={[hz.lat, hz.lon]}
              radius={hz.radiusKm * 1000}
              pathOptions={{ color: COLOR.hazard, fillOpacity: 0.12, weight: 2, dashArray: "5 5" }}
            >
              <Popup>{hz.label}</Popup>
            </Circle>
          ))}

        {visibility.routes &&
          layers?.fishingRoutes?.map((r) => (
            <Polyline key={r.id} positions={r.points} pathOptions={{ color: COLOR.route, weight: 2.5, dashArray: "1 7", lineCap: "round" }}>
              <Popup>{r.label}</Popup>
            </Polyline>
          ))}

        {visibility.boundary && layers?.boundary && (
          <Polyline positions={layers.boundary} pathOptions={{ color: COLOR.boundary, weight: 2, dashArray: "6 6" }} />
        )}

        {/* Mock illustrative harbour marker -- only shown as a last-resort
            placeholder when we don't have a real position yet (no GPS, no
            query/click result), so it never sits there impersonating your
            actual location once we know better. */}
        {layers?.landingCentre && !gpsCenter && !mapData?.current_position && (
          <Marker position={[layers.landingCentre.lat, layers.landingCentre.lon]} icon={pinIcon}>
            <Popup>{t("map.landingCentre")}</Popup>
          </Marker>
        )}

        {mapData?.pfz_zones?.map((z) => (
          <CircleMarker key={`turn-${z.zone_id}`} center={[z.lat, z.lon]} radius={10} pathOptions={{ color: COLOR.pfz, fillOpacity: 0.75, weight: 2.5 }}>
            <Popup>{z.zone_id}</Popup>
          </CircleMarker>
        ))}

        {mapData?.current_position && (
          <Marker position={[mapData.current_position.lat, mapData.current_position.lon]} icon={pinIcon}>
            <Popup>{t("map.currentPosition")}</Popup>
          </Marker>
        )}

        {mapData?.nearest_boundary_point && (
          <>
            <CircleMarker
              center={[mapData.nearest_boundary_point.lat, mapData.nearest_boundary_point.lon]}
              radius={7}
              pathOptions={{ color: COLOR.hazard, fillOpacity: 0.75, weight: 2 }}
            >
              <Popup>{t("map.nearestBoundaryPoint")}</Popup>
            </CircleMarker>
            {mapData.current_position && (
              <Polyline
                positions={[
                  [mapData.current_position.lat, mapData.current_position.lon],
                  [mapData.nearest_boundary_point.lat, mapData.nearest_boundary_point.lon],
                ]}
                pathOptions={{ color: COLOR.hazard, dashArray: "6 6", weight: 2 }}
              />
            )}
          </>
        )}

        {/* "You are here" marker from live GPS when query has no current_position */}
        {showGpsMarker && (
          <CircleMarker
            center={[gpsCenter.lat, gpsCenter.lon]}
            radius={8}
            pathOptions={{ color: COLOR.gps, fillColor: COLOR.gps, fillOpacity: 0.9, weight: 2 }}
          >
            <Popup>{t("map.currentPosition")}</Popup>
          </CircleMarker>
        )}
      </MapContainer>

      {!interactive && <div className={styles.previewOverlay} />}
      {!mapData && !layers && <div className={styles.hint}>{t("map.noData")}</div>}
    </div>
  );
}
