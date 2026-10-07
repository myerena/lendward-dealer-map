# Lendward dealer map

A searchable US dealer map built with Streamlit and Folium. Search a city and
state or ZIP, then pan and zoom to see nearby dealer entries. Click numbered
groups to expand overlapping pins. Dealer locations are approximate ZIP
locations and do not represent mailing territories or exclusive sales areas.
Optional 10, 25 and 50-mile rings show straight-line distance from the searched
city or ZIP center. Area searches update the view without rebuilding markers.
Rings are visual only, with no hover text or interception of map interactions.

Live app: https://dealer-map.streamlit.app/

## Run

Use Python 3.13. Install `requirements.txt`, then run `streamlit run app.py`.
On Streamlit Community Cloud, select this repository, branch `main`, file
`app.py`, and Python 3.13. No API keys or secrets are required.

## Data updates

The operator prepares a replacement `data/map_data.json` from each new complete
campaign export. This repository contains only the cleaned map snapshot. Raw
campaign exports, pricing, performance and employee assignments are excluded.
Some brand/name variants remain separate pending operator review.

## Attribution

ZIP and city locations are derived from [GeoNames](https://www.geonames.org/)
[US postal data](https://download.geonames.org/export/zip/US.zip), downloaded
October 7, 2026, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The saved lookup retains postal code, city, state and coordinate fields; city
centers are averages of listed ZIP locations. Searches use this saved lookup.
Map tiles are copyright [OpenStreetMap contributors](https://www.openstreetmap.org/copyright).
