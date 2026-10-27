# Myanmar Seismic Monitor

A static, interactive earthquake and active-fault dashboard. Open the [published site](https://geonet-myanmar.github.io/myanmar-earthquake-explorer-2007-2026/), or serve this directory locally:

```sh
python3 -m http.server 8000
```

Visit `http://localhost:8000/`. The HTML is self-contained, apart from the two local GeoJSON files and externally hosted Leaflet, Chart.js, fonts and map tiles. An internet connection is needed for those libraries and the basemap; `file://` is not supported because browsers restrict local data fetches.

GitHub Pages publishes the repository root from the `main` branch. Changes pushed to `main` are deployed automatically; no build step is required.

## Data and scope

- **Earthquakes:** [Thai Meteorological Department (TMD), Earthquake Observation Division regional archive](https://earthquake.tmd.go.th/inside.html). The export scans every page of the public regional event list and keeps rows whose Thai or English region label contains `เมียนมา`, `พม่า`, `Myanmar`, or `Burma`. It preserves the list's event ID, local and UTC times, magnitude, depth, phase count, region labels, felt indicator and link to the original event report. Missing numeric values are `null`. The point coordinates come from the list, which rounds them to 0.01°; individual TMD reports may have more precise coordinates.
- **Important limitations:** TMD describes that list as covering 2–25°N and 92–110°E. Events outside this box or not labeled Myanmar/Burma in the source are not included, even if they are geographically in Myanmar. It is not a complete national or global earthquake catalog, nor a live feed. Records and counts reflect the archived snapshot and may change at the source. Times and date filters use UTC. Unknown depths are excluded only when a maximum-depth filter is applied.
- **Active faults:** [GEM Global Active Faults Database](https://github.com/GEMScienceTools/gem-global-active-faults), original GeoJSON at commit `56816508ad92fd6846dad1163b1c8c01376a2cd1`. We select every original fault trace intersecting the Myanmar polygon from [Natural Earth 1:10m Admin 0 Countries](https://www.naturalearthdata.com/) at commit `9380cca83db5f9aef52d5e762765100745f84b27`. Complete traces and all GEM attributes are retained, so some lines extend into neighboring countries. This is an intersection-based selection, not an administrative classification or a clipped dataset. The fault count is not affected by earthquake filters.
- GEM data is licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Please retain attribution and follow that license when sharing derivatives. Citation: Styron, R. and Pagani, M. (2020). “The GEM Global Active Faults Database.” *Earthquake Spectra* 36(1_suppl), 160–180. [doi:10.1177/8755293020944182](https://doi.org/10.1177/8755293020944182). Natural Earth data is public domain. Consult TMD for terms governing reuse of its earthquake records.

Each GeoJSON includes source, selection and retrieval metadata. Data is intended for exploration, not emergency response, hazard prediction or engineering decisions.

## Refreshing the snapshot

The exporter requires Python 3, `requests`, `beautifulsoup4`, and `shapely`:

```sh
python3 -m pip install requests beautifulsoup4 shapely
python3 scripts/build_data.py
```

The script paginates TMD's entire regional archive with a small delay between requests, checks for missing or duplicate rows and detects common changes during pagination. If the archive changes mid-download, retry. GEM and boundary inputs are pinned to the commits above; change those pins deliberately when updating them. The output files are `data/myanmar-earthquakes.geojson` and `data/myanmar-active-faults.geojson`.
