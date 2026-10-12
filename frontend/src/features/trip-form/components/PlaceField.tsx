import Autocomplete from '@mui/material/Autocomplete'
import TextField from '@mui/material/TextField'
import { debounce } from '@mui/material/utils'
import { useEffect, useMemo, useState } from 'react'
import type { Place } from '../../../types/plan'
import { useGeocode } from '../api/geocode'

type Props = { label: string; value: Place | null; onChange: (place: Place | null) => void }

export function PlaceField({ label, value, onChange }: Props) {
  const [query, setQuery] = useState('')
  const updateQuery = useMemo(() => debounce(setQuery, 300), [])
  useEffect(() => () => updateQuery.clear(), [updateQuery])
  const { data = [], isFetching } = useGeocode(query)

  return (
    <Autocomplete
      value={value}
      options={value && !data.some((p) => p.label === value.label) ? [value, ...data] : data}
      filterOptions={(options) => options}
      getOptionLabel={(option) => option.label}
      isOptionEqualToValue={(a, b) => a.label === b.label}
      loading={isFetching}
      noOptionsText={query.trim().length < 3 ? 'Type 3 or more letters' : 'No US places found'}
      onInputChange={(_, text) => updateQuery(text)}
      onChange={(_, place) => onChange(place)}
      renderInput={(params) => <TextField {...params} label={label} required />}
    />
  )
}
