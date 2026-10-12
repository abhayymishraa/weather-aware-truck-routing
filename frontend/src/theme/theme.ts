import { createTheme } from '@mui/material/styles'

export const BRAND_PRIMARY = { light: '#063D4B', dark: '#5FB7CC' }

const FONT = "'Geist Variable', system-ui, sans-serif"

export const theme = createTheme({
  cssVariables: { colorSchemeSelector: 'class' },
  colorSchemes: {
    light: { palette: { primary: { main: BRAND_PRIMARY.light } } },
    dark: { palette: { primary: { main: BRAND_PRIMARY.dark } } },
  },
  shape: { borderRadius: 10 },
  typography: { fontFamily: FONT, button: { textTransform: 'none', fontWeight: 600 } },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          transition: 'transform 160ms cubic-bezier(0.23, 1, 0.32, 1)',
          '&:active': { transform: 'scale(0.97)' },
        },
      },
    },
  },
})
