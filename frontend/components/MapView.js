"use client";

import { useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  CircleMarker,
  Circle,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import styles from "./MapView.module.css";
import { useLocale } from "@/lib/i18n/LocaleContext";

// Imperatively re-centres the map when `center` or `zoom` changes, WITHOUT
// remounting the MapContainer. This is the safe alternative to putting a
// dynamic `key` on MapContainer, which would tear-down and rebuild the entire
// Leaflet instance on every data update and race with Leaflet's internal
// DOM-position tracking (`_leaflet_pos`), causing the runtime TypeError on
// repeated map clicks.
function MapRecenter({ lat, lon, zoom }) {
  const map = useMap();
  const prevRef = useRef(null);

  useEffect(() => {
    const prev = prevRef.current;
    if (!prev || prev.lat !== lat || prev.lon !== lon || prev.zoom !== zoom) {
      prevRef.current = { lat, lon, zoom };
      map.setView([lat, lon], zoom, { animate: true, duration: 0.5 });
    }
  }, [map, lat, lon, zoom]);

  return null;
}

// Leaflet's default marker icon paths are resolved relative to the bundler
// output and break under Next.js -- point them at the CDN copies instead.
const pinIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const DEFAULT_CENTER = { lat: 13.0827, lon: 80.2707 }; // Chennai, fallback only

// ClickHandler removed — search box is now the sole location-picker.

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
 * @param {() => void} [props.onPreviewClick] - Called when the non-interactive preview overlay is clicked.
 */
export default function MapView({
  mapData,
  layers,
  visibility = {},
  interactive = true,
  gpsCenter = null,
  onPreviewClick,
}) {
  const { t } = useLocale();

  // Center priority: query response > static layers > live GPS > Chennai default
  const center =
    mapData?.center ?? layers?.center ?? gpsCenter ?? DEFAULT_CENTER;
  const zoom = mapData?.zoom ?? layers?.zoom ?? 9;

  // Show a GPS marker only when we have a live position AND the query hasn't
  // already provided a current_position (to avoid double-pinning).
  const showGpsMarker = gpsCenter && !mapData?.current_position;

  // hazardZones/fishingRoutes have no real backend source (orchestration has
  // no hazard-zone or route data at all) -- they're fixed illustrative
  // markers sitting near Chennai's coordinates. Once we actually know where
  // the user is (real GPS or a clicked/queried point), keep showing them
  // would just mean stale Chennai pins next to the real location. Only show
  // them as a placeholder before we know any real position.
  const hasRealPosition = Boolean(gpsCenter || mapData?.current_position);

  return (
    <div className={styles.wrap}>
      <MapContainer
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
        className={styles.map}
      >
        {/* Re-centres the map imperatively on data updates -- avoids the
            MapContainer remount that caused the _leaflet_pos race condition. */}
        <MapRecenter lat={center.lat} lon={center.lon} zoom={zoom} />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {visibility.pfz &&
          layers?.pfzZones?.map((z) => (
            <CircleMarker
              key={z.id}
              center={[z.lat, z.lon]}
              radius={9}
              pathOptions={{ color: COLOR.pfz, fillOpacity: 0.55, weight: 2 }}
            >
              <Popup>{z.id}</Popup>
            </CircleMarker>
          ))}

        {visibility.hazard &&
          !hasRealPosition &&
          layers?.hazardZones?.map((hz) => (
            <Circle
              key={hz.id}
              center={[hz.lat, hz.lon]}
              radius={hz.radiusKm * 1000}
              pathOptions={{
                color: COLOR.hazard,
                fillOpacity: 0.12,
                weight: 2,
                dashArray: "5 5",
              }}
            >
              <Popup>{hz.label}</Popup>
            </Circle>
          ))}

        {visibility.routes &&
          !hasRealPosition &&
          layers?.fishingRoutes?.map((r) => (
            <Polyline
              key={r.id}
              positions={r.points}
              pathOptions={{
                color: COLOR.route,
                weight: 2.5,
                dashArray: "1 7",
                lineCap: "round",
              }}
            >
              <Popup>{r.label}</Popup>
            </Polyline>
          ))}

        {visibility.boundary && layers?.boundary && (
          <Polyline
            positions={layers.boundary}
            pathOptions={{ color: COLOR.boundary, weight: 2, dashArray: "6 6" }}
          />
        )}

        {layers?.landingCentre && (
          <Marker
            position={[layers.landingCentre.lat, layers.landingCentre.lon]}
            icon={pinIcon}
          >
            <Popup>{t("map.landingCentre")}</Popup>
          </Marker>
        )}

        {mapData?.pfz_zones?.map((z) => (
          <CircleMarker
            key={`turn-${z.zone_id}`}
            center={[z.lat, z.lon]}
            radius={10}
            pathOptions={{ color: COLOR.pfz, fillOpacity: 0.75, weight: 2.5 }}
          >
            <Popup>{z.zone_id}</Popup>
          </CircleMarker>
        ))}

        {mapData?.current_position && (
          <Marker
            position={[
              mapData.current_position.lat,
              mapData.current_position.lon,
            ]}
            icon={pinIcon}
          >
            <Popup>{t("map.currentPosition")}</Popup>
          </Marker>
        )}

        {mapData?.nearest_boundary_point && (
          <>
            <CircleMarker
              key="nearest-boundary-point"
              center={[
                mapData.nearest_boundary_point.lat,
                mapData.nearest_boundary_point.lon,
              ]}
              radius={7}
              pathOptions={{
                color: COLOR.hazard,
                fillOpacity: 0.75,
                weight: 2,
              }}
            >
              <Popup>{t("map.nearestBoundaryPoint")}</Popup>
            </CircleMarker>
            {mapData.current_position && (
              <Polyline
                positions={[
                  [mapData.current_position.lat, mapData.current_position.lon],
                  [
                    mapData.nearest_boundary_point.lat,
                    mapData.nearest_boundary_point.lon,
                  ],
                ]}
                pathOptions={{
                  color: COLOR.hazard,
                  dashArray: "6 6",
                  weight: 2,
                }}
              />
            )}
          </>
        )}

        {/* "You are here" marker from live GPS when query has no current_position */}
        {showGpsMarker && (
          <CircleMarker
            key="gps-position"
            center={[gpsCenter.lat, gpsCenter.lon]}
            radius={8}
            pathOptions={{
              color: COLOR.gps,
              fillColor: COLOR.gps,
              fillOpacity: 0.9,
              weight: 2,
            }}
          >
            <Popup>{t("map.currentPosition")}</Popup>
          </CircleMarker>
        )}
      </MapContainer>

      {/* Non-interactive preview overlay: transparent, but clickable so the
          user can tap it to open the full Map Explorer at the same position. */}
      {!interactive && (
        <div
          className={styles.previewOverlay}
          onClick={onPreviewClick}
          role="button"
          aria-label="Open full map"
        />
      )}
      {!mapData && !layers && (
        <div className={styles.hint}>{t("map.noData")}</div>
      )}
    </div>
  );
}
