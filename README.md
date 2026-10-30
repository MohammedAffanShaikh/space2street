# AMINA Space2Street

Satellite and public-weather context for Mumbai, Pune, Nagpur, Nashik and Thane.

## Local development

Requires Node.js 22.

```sh
npm install
npm run dev
```

Create and preview the production bundle with `npm run build` and `npm run preview`.

## Netlify deployment

Netlify uses the checked-in `netlify.toml`:

- Build command: `npm run build`
- Publish directory: `dist`
- Node.js: 22
- No secrets or environment variables are needed.

Client-side routes fall back to `index.html`. Push the project to a Git provider and import the repository in Netlify to deploy.

## Live data and limits

- Open-Meteo provides current model-estimated 2 m air temperature, apparent temperature, relative humidity, wind and precipitation; previous 24-hour rainfall; and forecast rainfall. Requests are refreshed on city change, manual refresh and every 15 minutes. Weather cells are model estimates near the selected city centre, not street sensors.
- NASA GIBS serves date-dependent MODIS Terra true-colour, daytime land-surface-temperature and 8-day NDVI browse tiles. Satellite layers are visual products; this app does not extract raster values or derive city-wide vegetation percentages.
- OpenStreetMap supplies the map base.
- Rainfall and elevation are context only. The application does not provide a flood forecast, flood boundary or official warning.
- When live weather retrieval fails, the app shows the error and retry control; it does not substitute sample values.

Data documentation is linked in the in-app Data & methodology page.
