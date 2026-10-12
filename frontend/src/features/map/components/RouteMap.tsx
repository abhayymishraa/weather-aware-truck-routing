import { useColorScheme } from '@mui/material/styles'
import { LngLatBounds } from 'maplibre-gl'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import Map, {
  AttributionControl,
  Layer,
  NavigationControl,
  Source,
  type MapLayerMouseEvent,
  type MapRef,
} from 'react-map-gl/maplibre'
import { MAP_STYLES, US_VIEW } from '../../../config/constants'
import { RISK_COLORS } from '../../../theme/risk'
import { BRAND_PRIMARY } from '../../../theme/theme'
import type { Route } from '../../../types/plan'
import {
  checkpointsToGeoJSON,
  routesToGeoJSON,
  type CheckpointFeatureProps,
} from '../utils/to-geojson'
import { CheckpointPopup } from './CheckpointPopup'

type Props = {
  routes: Route[]
  selectedId: number | null
  onSelect: (id: number) => void
  bottomInset?: number
  children?: ReactNode
}

type OpenPopup = { routes: Route[]; checkpoint: CheckpointFeatureProps }

const levelColor = [
  'match',
  ['get', 'level'],
  ...Object.entries(RISK_COLORS).flat(),
  RISK_COLORS.no_data,
] as unknown as string

export function RouteMap({ routes, selectedId, onSelect, bottomInset = 0, children }: Props) {
  const mapRef = useRef<MapRef>(null)
  const { mode, systemMode } = useColorScheme()
  const dark = (mode === 'system' ? systemMode : mode) === 'dark'
  const [popup, setPopup] = useState<OpenPopup | null>(null)
  const [cursor, setCursor] = useState('')

  const routeData = useMemo(() => routesToGeoJSON(routes), [routes])
  const checkpointData = useMemo(() => checkpointsToGeoJSON(routes), [routes])

  useEffect(() => {
    if (!routes.length) return
    const bounds = new LngLatBounds()
    for (const route of routes) {
      for (const [lon, lat] of route.geometry.coordinates) bounds.extend([lon, lat])
    }
    mapRef.current?.fitBounds(bounds, {
      padding: { top: 56, right: 56, left: 56, bottom: 48 + bottomInset },
      duration: 800,
    })
  }, [routes, bottomInset])

  function handleClick(event: MapLayerMouseEvent) {
    const feature = event.features?.[0]
    if (!feature) return
    if (feature.layer.id === 'checkpoints') {
      const props = feature.properties as CheckpointFeatureProps
      setPopup({ routes, checkpoint: props })
      onSelect(props.routeId)
    } else {
      onSelect(feature.properties.id as number)
    }
  }

  const selectedFilter = ['==', ['get', 'id'], selectedId ?? -1] as unknown as boolean

  return (
    <Map
      id="main"
      ref={mapRef}
      initialViewState={US_VIEW}
      mapStyle={dark ? MAP_STYLES.dark : MAP_STYLES.light}
      attributionControl={false}
      interactiveLayerIds={['route-hit', 'checkpoints']}
      onClick={handleClick}
      onMouseEnter={() => setCursor('pointer')}
      onMouseLeave={() => setCursor('')}
      cursor={cursor}
      style={{ width: '100%', height: '100%' }}
    >
      <NavigationControl position="top-right" showCompass={false} />
      <AttributionControl position="top-left" compact />
      {children}
      <Source id="routes" type="geojson" data={routeData}>
        <Layer
          id="route-line"
          type="line"
          layout={{ 'line-join': 'round', 'line-cap': 'round' }}
          paint={{ 'line-color': '#7d8b93', 'line-width': 4, 'line-opacity': 0.8 }}
        />
        <Layer
          id="route-selected-casing"
          type="line"
          filter={selectedFilter}
          layout={{ 'line-join': 'round', 'line-cap': 'round' }}
          paint={{ 'line-color': dark ? '#0b0f12' : '#ffffff', 'line-width': 9 }}
        />
        <Layer
          id="route-selected"
          type="line"
          filter={selectedFilter}
          layout={{ 'line-join': 'round', 'line-cap': 'round' }}
          paint={{ 'line-color': BRAND_PRIMARY[dark ? 'dark' : 'light'], 'line-width': 6 }}
        />
        <Layer
          id="route-hit"
          type="line"
          paint={{ 'line-color': '#000000', 'line-width': 18, 'line-opacity': 0 }}
        />
      </Source>
      <Source id="checkpoints" type="geojson" data={checkpointData}>
        <Layer
          id="checkpoints"
          type="circle"
          paint={{
            'circle-color': levelColor,
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 4, 10, 8],
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': 1.5,
          }}
        />
      </Source>
      {popup?.routes === routes && popup.checkpoint.routeId === selectedId && (
        <CheckpointPopup checkpoint={popup.checkpoint} onClose={() => setPopup(null)} />
      )}
    </Map>
  )
}
