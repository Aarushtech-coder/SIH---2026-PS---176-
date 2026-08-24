"use client";

import { MapContainer, TileLayer, Marker, Popup, Polyline, CircleMarker, Circle } from "react-leaflet";
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

const DEFAULT_CENTER = { lat: 13.0827, lon: 80.2707 }; // Chennai, placeholder

const COLOR = {
  pfz: "#16a34a",
  hazard: "#dc2626",
  route: "#2a6fdb",
  boundary: "#5b6b83",
  location: "#2a6fdb",
};

export default function MapView({ mapData, layers, visibility = {}, interactive = true }) {
  const { t } = useLocale();
  const center = mapData?.center ?? layers?.center ?? DEFAULT_CENTER;
  const zoom = mapData?.zoom ?? layers?.zoom ?? 9;

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
        className={styles.map}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

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

        {layers?.landingCentre && (
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
      </MapContainer>

      {!interactive && <div className={styles.previewOverlay} />}
      {!mapData && !layers && <div className={styles.hint}>{t("map.noData")}</div>}
    </div>
  );
}
