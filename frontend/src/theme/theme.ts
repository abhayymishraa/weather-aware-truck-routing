import { createTheme } from '@mui/material/styles'

export const BRAND_PRIMARY = { light: '#063D4B', dark: '#5FB7CC' }

export const theme = createTheme({
  cssVariables: { colorSchemeSelector: 'class' },
  colorSchemes: {
    light: { palette: { primary: { main: BRAND_PRIMARY.light } } },
    dark: { palette: { primary: { main: BRAND_PRIMARY.dark } } },
  },
  shape: { borderRadius: 10 },
})
